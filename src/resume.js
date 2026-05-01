import { readFile } from "node:fs/promises";
import pdf from "pdf-parse";

const TITLE_HINTS = [
  "Java Backend Developer",
  "Spring Boot Developer",
  "Java Microservices Developer",
  "Backend Engineer",
  "Java Cloud Backend Developer",
  "AI-assisted Backend Developer"
];

const SKILL_MAP = [
  "java",
  "spring boot",
  "spring mvc",
  "helidon",
  "rest api",
  "openapi",
  "swagger",
  "microservices",
  "sql",
  "oracle database",
  "kafka",
  "redis",
  "junit",
  "mockito",
  "postman",
  "docker",
  "kubernetes",
  "helm",
  "maven",
  "git",
  "aws",
  "azure",
  "claude",
  "codex",
  "cline",
  "mcp",
  "prompt engineering",
  "system design",
  "oop",
  "dsa"
];

export async function parseResume(resumePath) {
  const buffer = await readFile(resumePath);
  const parsed = await pdf(buffer);
  const text = parsed.text.replace(/\s+/g, " ").trim();
  const lower = text.toLowerCase();
  const skills = SKILL_MAP.filter((skill) => lower.includes(skill));

  return {
    path: resumePath,
    text,
    strongestSkills: skills,
    bestFitTitles: TITLE_HINTS,
    years: lower.includes("4+ years") ? 4 : null
  };
}

