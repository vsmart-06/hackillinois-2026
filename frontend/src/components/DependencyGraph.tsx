import { useEffect, useRef, useMemo } from "react";
import type { CourseEntry } from "./ClassList";

// Mock adjacency list — simulates API response
const MOCK_DEPENDENCIES: Record<string, string[]> = {
  "CS 101": [],
  "CS 201": ["CS 101"],
  "CS 301": ["CS 201", "MATH 201"],
  "CS 401": ["CS 301"],
  "MATH 101": [],
  "MATH 201": ["MATH 101"],
  "MATH 301": ["MATH 201"],
  "STAT 201": ["MATH 201"],
  "STAT 301": ["STAT 201", "CS 201"],
  "ECE 201": ["MATH 101", "PHYS 101"],
  "PHYS 101": [],
  "PHYS 201": ["PHYS 101", "MATH 201"],
};

interface Node {
  id: string;
  x: number;
  y: number;
}

interface Edge {
  from: string;
  to: string;
}

interface DependencyGraphProps {
  courses: CourseEntry[];
}

const DependencyGraph = ({ courses }: DependencyGraphProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const completeCourses = useMemo(
    () =>
      courses
        .filter((c) => c.department && c.courseNumber)
        .map((c) => `${c.department} ${c.courseNumber}`),
    [courses]
  );

  // Build subgraph from mock data
  const { nodes, edges } = useMemo(() => {
    if (completeCourses.length === 0) return { nodes: [], edges: [] };

    const relevant = new Set<string>();
    const edgeList: Edge[] = [];

    // Add entered courses and their dependencies
    for (const course of completeCourses) {
      relevant.add(course);
      const deps = MOCK_DEPENDENCIES[course];
      if (deps) {
        for (const dep of deps) {
          relevant.add(dep);
          edgeList.push({ from: dep, to: course });
        }
      }
    }

    // Also check if any relevant course is a dependency of another relevant course
    for (const course of relevant) {
      const deps = MOCK_DEPENDENCIES[course];
      if (deps) {
        for (const dep of deps) {
          if (relevant.has(dep)) {
            const exists = edgeList.some((e) => e.from === dep && e.to === course);
            if (!exists) edgeList.push({ from: dep, to: course });
          }
        }
      }
    }

    // Layout: topological sort into layers
    const inDegree: Record<string, number> = {};
    const adjList: Record<string, string[]> = {};
    for (const id of relevant) {
      inDegree[id] = 0;
      adjList[id] = [];
    }
    for (const e of edgeList) {
      if (relevant.has(e.from) && relevant.has(e.to)) {
        adjList[e.from].push(e.to);
        inDegree[e.to] = (inDegree[e.to] || 0) + 1;
      }
    }

    const layers: string[][] = [];
    let queue = Object.keys(inDegree).filter((k) => inDegree[k] === 0);
    const visited = new Set<string>();

    while (queue.length > 0) {
      layers.push([...queue]);
      const next: string[] = [];
      for (const node of queue) {
        visited.add(node);
        for (const neighbor of adjList[node] || []) {
          inDegree[neighbor]--;
          if (inDegree[neighbor] === 0 && !visited.has(neighbor)) {
            next.push(neighbor);
          }
        }
      }
      queue = next;
    }

    // Position nodes
    const nodeList: Node[] = [];
    const padding = 60;
    const layerHeight = 70;
    const canvasWidth = 550;

    layers.forEach((layer, li) => {
      const layerWidth = layer.length;
      layer.forEach((id, ni) => {
        nodeList.push({
          id,
          x: padding + ((ni + 0.5) / layerWidth) * (canvasWidth - padding * 2),
          y: padding + li * layerHeight,
        });
      });
    });

    return { nodes: nodeList, edges: edgeList };
  }, [completeCourses]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Center the graph horizontally: compute offset from layout width to actual canvas width
    const layoutWidth = 550;
    const offsetX = (w - layoutWidth) / 2;

    if (nodes.length === 0) return;

    ctx.save();
    ctx.translate(offsetX, 0);

    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    // Draw edges with proper arrowheads
    ctx.strokeStyle = "hsl(20 100% 51% / 0.4)";
    ctx.lineWidth = 1.5;
    for (const edge of edges) {
      const from = nodeMap.get(edge.from);
      const to = nodeMap.get(edge.to);
      if (from && to) {
        // Calculate the endpoint at the edge of the target node box
        const boxH = 28;
        const targetY = to.y - boxH / 2; // top edge of target node

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        const midY = (from.y + targetY) / 2;
        ctx.bezierCurveTo(from.x, midY, to.x, midY, to.x, targetY);
        ctx.stroke();

        // Arrowhead — compute tangent at endpoint of bezier
        const t = 0.95;
        const t1 = 1 - t;
        // Derivative of cubic bezier at t
        const dx = 3 * t1 * t1 * (from.x - from.x) + 6 * t1 * t * (to.x - from.x) + 3 * t * t * (to.x - to.x);
        const dy = 3 * t1 * t1 * (midY - from.y) + 6 * t1 * t * (midY - midY) + 3 * t * t * (targetY - midY);
        const angle = Math.atan2(dy, dx);

        const arrowSize = 7;
        ctx.fillStyle = "hsl(20 100% 51% / 0.7)";
        ctx.beginPath();
        ctx.moveTo(to.x, targetY);
        ctx.lineTo(
          to.x - arrowSize * Math.cos(angle - Math.PI / 6),
          targetY - arrowSize * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
          to.x - arrowSize * Math.cos(angle + Math.PI / 6),
          targetY - arrowSize * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();
      }
    }

    // Draw nodes
    for (const node of nodes) {
      const isUserCourse = completeCourses.includes(node.id);

      // Node background
      ctx.fillStyle = isUserCourse
        ? "hsl(20 100% 51%)"
        : "hsl(218 50% 24%)";
      const textWidth = ctx.measureText(node.id).width;
      const boxW = Math.max(textWidth + 24, 70);
      const boxH = 28;
      const rx = 6;

      // Rounded rect
      ctx.beginPath();
      ctx.moveTo(node.x - boxW / 2 + rx, node.y - boxH / 2);
      ctx.lineTo(node.x + boxW / 2 - rx, node.y - boxH / 2);
      ctx.quadraticCurveTo(node.x + boxW / 2, node.y - boxH / 2, node.x + boxW / 2, node.y - boxH / 2 + rx);
      ctx.lineTo(node.x + boxW / 2, node.y + boxH / 2 - rx);
      ctx.quadraticCurveTo(node.x + boxW / 2, node.y + boxH / 2, node.x + boxW / 2 - rx, node.y + boxH / 2);
      ctx.lineTo(node.x - boxW / 2 + rx, node.y + boxH / 2);
      ctx.quadraticCurveTo(node.x - boxW / 2, node.y + boxH / 2, node.x - boxW / 2, node.y + boxH / 2 - rx);
      ctx.lineTo(node.x - boxW / 2, node.y - boxH / 2 + rx);
      ctx.quadraticCurveTo(node.x - boxW / 2, node.y - boxH / 2, node.x - boxW / 2 + rx, node.y - boxH / 2);
      ctx.closePath();
      ctx.fill();

      // Text
      ctx.fillStyle = "hsl(0 0% 100%)";
      ctx.font = "bold 11px 'DM Sans', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(node.id, node.x, node.y);
    }

    ctx.restore();
  }, [nodes, edges, completeCourses]);

  const graphHeight = Math.max(300, nodes.length > 0 ? (Math.max(...nodes.map((n) => n.y)) + 60) : 300);

  return (
    <div className="flex flex-col items-center">
      {completeCourses.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          Add classes in the sidebar to see their dependency graph.
        </p>
      ) : (
        <canvas
          ref={canvasRef}
          className="w-full rounded-lg"
          style={{ height: graphHeight }}
        />
      )}
    </div>
  );
};

export default DependencyGraph;
