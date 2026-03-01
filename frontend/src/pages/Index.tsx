import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import ClassList, { type CourseEntry } from "@/components/ClassList";
import DependencyGraph from "@/components/DependencyGraph";
import SemflowLogo from "@/components/SemflowLogo";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { GitBranch } from "lucide-react";

interface Message {
  id: string;
  content: string;
  role: "user" | "bot";
}

const MOCK_RESPONSES = [
  "I can help you with that! Based on your classes, you might want to consider spreading your workload across the week.",
  "That's a great course combo. Make sure to check for prerequisite requirements before enrolling.",
  "I'd recommend checking the professor ratings for that section — it can make a big difference.",
  "Looks like that class fills up fast — register as early as possible during your enrollment window.",
  "Based on your schedule, you have a gap on Tuesdays and Thursdays that could fit another elective.",
];

const Index = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [courses, setCourses] = useState<CourseEntry[]>([
    { id: "1", department: "", courseNumber: "" },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasMessages = messages.length > 0;

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const handleSend = (content: string) => {
    const userMsg: Message = { id: Date.now().toString(), content, role: "user" };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    setTimeout(() => {
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        content: MOCK_RESPONSES[Math.floor(Math.random() * MOCK_RESPONSES.length)],
        role: "bot",
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsTyping(false);
    }, 1200 + Math.random() * 800);
  };

  const addCourse = () => {
    setCourses((prev) => [
      ...prev,
      { id: Date.now().toString(), department: "", courseNumber: "" },
    ]);
  };

  const removeCourse = (id: string) => {
    setCourses((prev) => prev.filter((c) => c.id !== id));
  };

  const updateCourse = (id: string, field: "department" | "courseNumber", value: string) => {
    setCourses((prev) => prev.map((c) => (c.id === id ? { ...c, [field]: value } : c)));
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-center bg-primary px-6 py-3">
          <SemflowLogo size={28} />
        </header>

        <div className="relative flex flex-1 flex-col overflow-hidden">
          <AnimatePresence mode="wait">
            {!hasMessages ? (
              <motion.div
                key="welcome"
                exit={{ opacity: 0, y: -30 }}
                transition={{ duration: 0.3 }}
                className="absolute inset-0 flex flex-col items-center justify-center px-4"
              >
                <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                  <SemflowLogo size={40} />
                </div>
                <h2 className="mb-2 text-2xl font-bold text-foreground">What can I help with?</h2>
                <p className="mb-10 max-w-md text-center text-sm text-muted-foreground">
                  Ask me about courses, scheduling conflicts, prerequisites, or add your classes in the sidebar to get personalized advice.
                </p>
                <ChatInput onSend={handleSend} disabled={isTyping} centered />
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-1 flex-col overflow-hidden"
              >
                <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
                  <div className="mx-auto max-w-2xl space-y-3">
                    {messages.map((msg) => (
                      <ChatMessage key={msg.id} content={msg.content} role={msg.role} />
                    ))}
                    {isTyping && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                        <div className="rounded-2xl rounded-bl-md bg-chat-bot px-4 py-3">
                          <div className="flex gap-1">
                            {[0, 1, 2].map((i) => (
                              <motion.span
                                key={i}
                                className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50"
                                animate={{ y: [0, -4, 0] }}
                                transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                              />
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </div>
                </div>
                <div className="mx-auto w-full max-w-2xl px-6 pb-4 pt-2">
                  <ChatInput onSend={handleSend} disabled={isTyping} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Right sidebar */}
      <aside className="hidden w-64 flex-shrink-0 border-l border-sidebar-border bg-sidebar md:flex md:flex-col">
        <ClassList
          courses={courses}
          onAdd={addCourse}
          onRemove={removeCourse}
          onUpdate={updateCourse}
        />
        <div className="flex-1" />
        <div className="border-t border-sidebar-border p-4">
          <Dialog>
            <DialogTrigger asChild>
              <button className="flex w-full items-center justify-center gap-2 rounded-lg bg-sidebar-primary px-4 py-2.5 text-sm font-semibold text-sidebar-primary-foreground transition-colors hover:bg-sidebar-primary/90">
                <GitBranch size={16} />
                View Prerequisites
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Prerequisite Graph</DialogTitle>
              </DialogHeader>
              <DependencyGraph courses={courses} />
            </DialogContent>
          </Dialog>
        </div>
      </aside>
    </div>
  );
};

export default Index;
