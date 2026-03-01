"""Modal endpoint for Llama 3 8B course recommendation inference.

Deploy with: modal deploy modal/modal_inference.py
Then call via HTTP POST to the deployed URL, or use the FastAPI backend proxy at POST /api/recommend.
"""

import modal

app = modal.App("semflow-inference")

# Build image with vllm for fast inference
inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm==0.3.3",
        "torch==2.1.0",
        "transformers>=4.38.0",
        "accelerate>=0.27.0",
        "huggingface_hub>=0.20.0",
    )
)

# Model ID from HuggingFace
MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"

# Store model weights in a Modal Volume so we don't re-download on every cold start
volume = modal.Volume.from_name("semflow-model-weights", create_if_missing=True)
MODEL_DIR = "/model"


@app.cls(
    image=inference_image,
    gpu="A10G",  # A10G is cost-effective and fast enough for 8B model
    keep_warm=1,  # Critical for demo — avoid cold start
    container_idle_timeout=300,
    volumes={MODEL_DIR: volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],  # HF_TOKEN for Llama access
    timeout=300,
)
class LlamaInference:
    @modal.enter()
    def load_model(self):
        from vllm import LLM, SamplingParams

        self.llm = LLM(
            model=MODEL_ID,
            download_dir=MODEL_DIR,
            dtype="float16",
            max_model_len=8192,
        )
        self.sampling_params = SamplingParams(
            temperature=0.3,  # Low temp for more consistent recommendations
            top_p=0.9,
            max_tokens=2048,
        )

    @modal.method()
    def recommend(self, prompt: str) -> str:
        outputs = self.llm.generate([prompt], self.sampling_params)
        return outputs[0].outputs[0].text.strip()


def build_prompt(
    goals: str,
    completed_courses: list[str],
    candidate_courses: list[dict],
) -> str:
    """Build the recommendation prompt with student profile and candidate courses."""
    completed_str = ", ".join(completed_courses) if completed_courses else "None"

    courses_str = ""
    for i, c in enumerate(candidate_courses, 1):
        courses_str += f"""
Course {i}: {c.get('subject', '')} {c.get('courseNumber', '')} - {c.get('title', '')}
Description: {c.get('description', 'N/A')}
Prerequisites: {c.get('prerequisites', 'None')}
Average GPA: {c.get('avg_gpa', 'N/A')}
"""

    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert academic advisor at the University of Illinois Urbana-Champaign (UIUC).
Your job is to recommend courses to students based on their goals and background.
Always respond in valid JSON format only. No prose outside the JSON.
<|eot_id|><|start_header_id|>user<|end_header_id|>

Student Profile:
- Goals/Interests: {goals}
- Completed Courses: {completed_str}

Candidate Courses:
{courses_str}

Please recommend the most relevant courses from the list above.
Return a JSON object with exactly this structure:
{{
  "can_take_now": [
    {{
      "subject": "CS",
      "course_number": "225",
      "title": "Data Structures",
      "reason": "Why this course fits the student's goals",
      "avg_gpa": 3.2
    }}
  ],
  "work_toward": [
    {{
      "subject": "CS",
      "course_number": "446",
      "title": "Machine Learning",
      "reason": "Why this is a great long-term goal",
      "missing_prerequisites": ["CS 357"],
      "avg_gpa": 3.1
    }}
  ]
}}

Only include courses from the candidate list. Prioritize fit to goals over GPA.
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""


@app.function(image=inference_image, keep_warm=1)
@modal.web_endpoint(method="POST")
def recommend_endpoint(payload: dict) -> dict:
    """
    POST body:
    {
        "goals": "I want to go into ML engineering",
        "completed_courses": ["CS 225", "MATH 241"],
        "candidate_courses": [ ...list of course dicts from your vector store... ]
    }

    Course dicts should have: subject, courseNumber, title, description, prerequisites (optional: avg_gpa).
    Matches Semflow backend Course shape from GET /api/courses/{subject} and storage.

    Returns:
    {
        "can_take_now": [...],
        "work_toward": [...]
    }
    """
    import json

    goals = payload.get("goals", "")
    completed_courses = payload.get("completed_courses", [])
    candidate_courses = payload.get("candidate_courses", [])

    if not goals or not candidate_courses:
        return {"error": "goals and candidate_courses are required"}

    prompt = build_prompt(goals, completed_courses, candidate_courses)

    inferencer = LlamaInference()
    raw_output = inferencer.recommend.remote(prompt)

    # Parse JSON response from model
    try:
        # Strip any accidental markdown fences
        clean = raw_output.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: return raw text if JSON parsing fails
        result = {"raw": raw_output, "error": "Failed to parse model output as JSON"}

    return result
