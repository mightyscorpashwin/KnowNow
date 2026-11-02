import { useState } from "react";
import type { PageContent } from "../types";

type Question = PageContent["quiz"][number];

function QuizItem({ q, n }: { q: Question; n: number }) {
  const [picked, setPicked] = useState<number | null>(null);
  const answered = picked !== null;
  return (
    <fieldset className="quiz-item">
      <legend>
        <span className="quiz-n">{n}.</span> {q.question}
      </legend>
      <div className="quiz-options">
        {q.options.map((opt, i) => {
          const state = !answered ? "" : i === q.answerIndex ? "right" : i === picked ? "wrong" : "";
          return (
            <button
              key={i}
              type="button"
              className={`quiz-option ${state}`}
              disabled={answered}
              aria-pressed={picked === i}
              onClick={() => setPicked(i)}
            >
              {opt}
            </button>
          );
        })}
      </div>
      {answered && (
        <p className="quiz-feedback" role="status">
          <strong>{picked === q.answerIndex ? "Correct." : "Not quite."}</strong> {q.explanation}
        </p>
      )}
    </fieldset>
  );
}

export default function Quiz({ questions }: { questions: Question[] }) {
  return (
    <div className="quiz">
      {questions.map((q, i) => (
        <QuizItem key={i} q={q} n={i + 1} />
      ))}
    </div>
  );
}
