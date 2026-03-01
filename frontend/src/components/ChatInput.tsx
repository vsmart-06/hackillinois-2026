import { useState } from "react";
import { Mic, MicOff, Send } from "lucide-react";
import { motion } from "framer-motion";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  centered?: boolean;
  children?: React.ReactNode;
}

const ChatInput = ({ onSend, disabled, centered, children }: ChatInputProps) => {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleVoice = () => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    setIsListening(true);
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? prev + " " + transcript : transcript));
      setIsListening(false);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  return (
    <div className={centered ? "w-full max-w-lg" : "w-full"}>
      <div className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-lg shadow-foreground/5 transition-all">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about courses, schedules, prerequisites..."
          rows={1}
          disabled={disabled}
          className="min-h-[40px] max-h-[120px] flex-1 resize-none bg-transparent px-3 py-2 text-sm text-card-foreground placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-50"
        />

        <button
          onClick={toggleVoice}
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border-2 transition-all ${
            isListening
              ? "border-primary bg-destructive text-destructive-foreground animate-pulse"
              : "border-primary bg-accent text-accent-foreground hover:bg-accent/80"
          }`}
        >
          {isListening ? <MicOff size={16} className="text-destructive-foreground" /> : <Mic size={16} className="text-primary" />}
        </button>

        <motion.button
          whileTap={{ scale: 0.92 }}
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-opacity disabled:opacity-30"
        >
          <Send size={16} />
        </motion.button>
      </div>
      {children}
    </div>
  );
};

export default ChatInput;
