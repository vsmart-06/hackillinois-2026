import { Plus, X, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useRef } from "react";

export interface CourseEntry {
  id: string;
  department: string;
  courseNumber: string;
}

const DEPARTMENTS = ["CS", "MATH", "STAT", "ECE", "PHYS", "CHEM", "ECON"];

interface ClassListProps {
  courses: CourseEntry[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, field: "department" | "courseNumber", value: string) => void;
}

const ClassList = ({ courses, onAdd, onRemove, onUpdate }: ClassListProps) => {
  return (
    <div className="flex flex-col">
      {/* Header area — extends orange bar */}
      <div className="flex items-center justify-between bg-primary px-6 py-3">
        <span className="text-sm font-bold uppercase tracking-widest text-primary-foreground">
          My Classes
        </span>
        <button
          onClick={onAdd}
          className="flex items-center gap-1 rounded-lg bg-white/20 px-2.5 py-1 text-xs font-medium text-primary-foreground transition-colors hover:bg-white/30"
        >
          <Plus size={12} />
          Add
        </button>
      </div>

      <div className="flex flex-col items-center space-y-2 px-5 py-4">
        <AnimatePresence mode="popLayout">
          {courses.map((course, index) => {
            const isComplete = !!(course.department && course.courseNumber);

            return (
              <motion.div
                key={course.id}
                layout
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2, delay: index * 0.03 }}
                className="flex items-center gap-1.5"
              >
                <DepartmentSelect
                  value={course.department}
                  onChange={(val) => onUpdate(course.id, "department", val)}
                  highlighted={isComplete}
                />
                <input
                  type="text"
                  placeholder="###"
                  value={course.courseNumber}
                  onChange={(e) =>
                    onUpdate(course.id, "courseNumber", e.target.value)
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      const hasIncomplete = courses.some((c) => !c.department || !c.courseNumber);
                      if (!hasIncomplete) onAdd();
                    }
                  }}
                  className={`w-14 rounded-lg border bg-sidebar-accent px-2.5 py-2 text-xs font-medium tracking-wide text-sidebar-foreground placeholder:text-sidebar-muted focus:outline-none focus:ring-2 focus:ring-sidebar-primary/50 ${
                    isComplete
                      ? "border-sidebar-primary"
                      : "border-sidebar-border"
                  }`}
                  maxLength={5}
                />
                <button
                  onClick={() => onRemove(course.id)}
                  className="rounded-md p-1 text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
                >
                  <X size={13} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {courses.length === 0 && (
          <p className="py-6 text-center text-xs text-sidebar-muted">
            No classes added yet
          </p>
        )}
      </div>
    </div>
  );
};

function DepartmentSelect({
  value,
  onChange,
  highlighted,
}: {
  value: string;
  onChange: (val: string) => void;
  highlighted: boolean;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex w-[5rem] items-center justify-between rounded-lg border bg-sidebar-accent px-2.5 py-2 text-xs font-medium uppercase tracking-wide text-sidebar-foreground transition-all focus:outline-none focus:ring-2 focus:ring-sidebar-primary/50 ${
          highlighted ? "border-sidebar-primary" : "border-sidebar-border"
        }`}
      >
        <span className={value ? "text-sidebar-foreground" : "text-sidebar-muted"}>
          {value || "DEPT"}
        </span>
        <ChevronDown size={12} className="text-sidebar-muted" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 top-full z-50 mt-1 w-[5rem] overflow-hidden rounded-lg border border-sidebar-border bg-sidebar-accent shadow-xl"
          >
            {DEPARTMENTS.map((dept) => (
              <button
                key={dept}
                onClick={() => {
                  onChange(dept);
                  setOpen(false);
                }}
                className={`block w-full px-2.5 py-1.5 text-left text-xs font-medium uppercase tracking-wide transition-colors hover:bg-sidebar-primary/20 hover:text-sidebar-primary ${
                  value === dept
                    ? "bg-sidebar-primary/10 text-sidebar-primary"
                    : "text-sidebar-foreground"
                }`}
              >
                {dept}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ClassList;
