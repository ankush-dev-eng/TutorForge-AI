'use client';

import { useState } from 'react';
import { assessmentApi, DiagnosticState, AnswerSubmitResponse } from '@/lib/api';
import { Brain, CheckCircle2, XCircle, ArrowRight, Play, Trophy } from 'lucide-react';

export default function AssessmentView() {
  const [diagnosticState, setDiagnosticState] = useState<DiagnosticState | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [answerResult, setAnswerResult] = useState<AnswerSubmitResponse | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startAssessment = async () => {
    setLoading(true);
    setDiagnosticState(null);
    setAnswerResult(null);
    setSelectedOption('');
    setCompleted(false);
    setError(null);
    try {
      const data = await assessmentApi.start();
      if (!data || !data.question) {
        setError('Failed to start assessment: No question received.');
      } else {
        setDiagnosticState(data);
        setQuestionNumber(1);
        setStartTime(Date.now());
      }
    } catch (e) {
      console.error(e);
      setError((e as Error).message || 'An error occurred starting the assessment.');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!diagnosticState || !diagnosticState.question || !selectedOption || answerResult) return;
    
    setLoading(true);
    const timeMs = Date.now() - startTime;
    
    try {
      const result = await assessmentApi.submit(
        diagnosticState.assessment_id, 
        diagnosticState.question.id, 
        selectedOption, 
        timeMs
      );
      setAnswerResult(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const nextQuestion = () => {
    if (!diagnosticState || !answerResult) return;
    
    if (answerResult.next_question) {
      setDiagnosticState({
        ...diagnosticState,
        question: answerResult.next_question,
        difficulty: answerResult.next_difficulty,
        difficulty_label: answerResult.next_difficulty_label,
        mastery_before: answerResult.mastery_after
      });
      setQuestionNumber(prev => prev + 1);
      setSelectedOption('');
      setAnswerResult(null);
      setStartTime(Date.now());
    } else {
      // Completed assessment
      setCompleted(true);
    }
  };

  if (completed) {
    return (
      <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto space-y-8 animate-in fade-in duration-700">
        <div className="w-16 h-16 bg-sage/10 flex items-center justify-center rounded-lg border border-sage/20">
          <Trophy className="w-8 h-8 text-sage" />
        </div>
        <div className="text-center">
          <h2 className="text-3xl font-semibold mb-4 tracking-tight">Diagnostic Complete</h2>
          <p className="text-muted-foreground text-base mb-8 leading-relaxed max-w-lg mx-auto">
            You have completed this adaptive assessment. Your mastery levels have been updated.
          </p>
        </div>
        <button 
          onClick={() => {
            setCompleted(false);
            setDiagnosticState(null);
          }}
          className="bg-primary text-primary-foreground px-8 py-3.5 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Back to Assessments
        </button>
      </div>
    );
  }

  if (!diagnosticState || !diagnosticState.question) {
    return (
      <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto space-y-8 animate-in fade-in duration-700">
        <div className="w-16 h-16 bg-muted/30 flex items-center justify-center rounded-lg border border-border/40">
          <Brain className="w-8 h-8 text-primary/80" />
        </div>
        <div className="text-center">
          <h2 className="text-3xl font-semibold mb-4 tracking-tight">Diagnostic Assessment</h2>
          <p className="text-muted-foreground text-base mb-8 leading-relaxed max-w-lg mx-auto">
            Evaluate your current mastery level through an adaptive diagnostic process. Questions will calibrate in real-time to precisely gauge your comprehension.
          </p>
          {error && (
            <p className="text-terracotta mb-8 p-4 bg-terracotta/10 border border-terracotta/20 rounded">
              {error}
            </p>
          )}
        </div>
        <button 
          onClick={startAssessment}
          disabled={loading}
          className="group flex items-center justify-center gap-2 bg-primary text-primary-foreground px-8 py-3.5 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 min-w-50"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin"></span>
              Initializing
            </span>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Start Diagnostic
            </>
          )}
        </button>
      </div>
    );
  }

  const q = diagnosticState.question;

  return (
    <div className="flex flex-col h-full w-full max-w-3xl mx-auto py-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header & Progress */}
      <div className="mb-8">
        <div className="flex justify-between items-end text-xs font-medium text-muted-foreground mb-3 tracking-widest uppercase">
          <span>Question {questionNumber}</span>
          <span className="flex items-center gap-2">
            <span>Difficulty</span>
            <span className={`px-2 py-0.5 border ${
              diagnosticState.difficulty === 1 ? 'border-sage/30 text-sage bg-sage/5' : 
              diagnosticState.difficulty === 2 ? 'border-accent/30 text-accent bg-accent/5' : 
              'border-terracotta/30 text-terracotta bg-terracotta/5'
            }`}>
              {diagnosticState.difficulty_label}
            </span>
          </span>
        </div>
        <div className="h-1 w-full bg-muted overflow-hidden relative">
          {/* Continuous progress bar for adaptive tests (just simple animation) */}
          <div className="h-full bg-primary/40 w-full" />
        </div>
      </div>

      {/* Question Card */}
      <div className="bg-card border border-border/40 p-8 md:p-10 flex-1 flex flex-col shadow-sm">
        <h3 className="text-xl md:text-2xl font-medium mb-10 leading-snug">
          {q.text}
        </h3>

        <div className="space-y-3 mb-8 flex-1">
          {(!q.options || q.options.length === 0) ? (
            <div className="w-full">
              <textarea
                value={selectedOption}
                onChange={(e) => !answerResult && setSelectedOption(e.target.value)}
                disabled={!!answerResult || loading}
                placeholder="Type your answer here..."
                className="w-full min-h-30 p-4 border border-border bg-background focus:outline-none focus:border-primary text-foreground disabled:opacity-50 resize-none transition-colors"
              />
              {answerResult && (
                <div className="mt-4 p-4 border border-border/40 bg-muted/20">
                  <p className="text-sm text-muted-foreground mb-1">Expected Answer:</p>
                  <p className="font-medium">{answerResult.correct_answer}</p>
                </div>
              )}
            </div>
          ) : (
            q.options.map((opt, idx) => {
              const isSelected = selectedOption === opt;
              let btnClass = "w-full text-left p-4 md:p-5 border text-sm md:text-base transition-colors flex items-center gap-4 ";
              
              if (answerResult) {
                const isCorrectOpt = opt === answerResult.correct_answer;
                if (isCorrectOpt) {
                  btnClass += "bg-sage/5 border-sage/30 text-foreground";
                } else if (isSelected && !answerResult.is_correct) {
                  btnClass += "bg-terracotta/5 border-terracotta/30 text-foreground";
                } else {
                  btnClass += "opacity-50 border-border/40 bg-muted/20";
                }
              } else {
                btnClass += isSelected 
                  ? "border-primary bg-primary/5 text-foreground" 
                  : "border-border/40 hover:border-primary/40 hover:bg-muted/30 text-foreground";
              }

              return (
                <button 
                  key={idx}
                  onClick={() => !answerResult && setSelectedOption(opt)}
                  disabled={!!answerResult || loading}
                  className={btnClass}
                >
                  <div className={`h-5 w-5 border flex items-center justify-center shrink-0 transition-colors ${
                    isSelected && !answerResult ? 'border-primary' : 'border-muted-foreground/40'
                  }`}>
                    {isSelected && !answerResult && <div className="h-2.5 w-2.5 bg-primary" />}
                    {answerResult && opt === answerResult.correct_answer && <CheckCircle2 className="w-5 h-5 text-sage" />}
                    {answerResult && isSelected && !answerResult.is_correct && <XCircle className="w-5 h-5 text-terracotta" />}
                  </div>
                  <span className="font-medium">{opt}</span>
                </button>
              );
            })
          )}
        </div>

        {/* Feedback Section */}
        {answerResult && (
          <div className={`p-5 md:p-6 mb-8 border animate-in fade-in duration-300 ${
            answerResult.is_correct ? 'bg-sage/5 border-sage/20' : 'bg-terracotta/5 border-terracotta/20'
          }`}>
            <h4 className={`text-sm font-semibold mb-2 flex items-center gap-2 uppercase tracking-wide ${
              answerResult.is_correct ? 'text-sage' : 'text-terracotta'
            }`}>
              {answerResult.is_correct ? (
                <><CheckCircle2 className="w-4 h-4" /> Mastery Demonstrated</>
              ) : (
                <><Brain className="w-4 h-4" /> Learning Opportunity</>
              )}
              {answerResult.is_correct && answerResult.badges_earned && answerResult.badges_earned.length > 0 && (
                <span className="ml-auto text-xs flex items-center gap-1.5 px-2 py-0.5 border border-brass/30 bg-brass-soft text-brass">
                  <Trophy className="w-3 h-3" />
                  {answerResult.badges_earned[0]}
                </span>
              )}
            </h4>
            <p className="text-foreground/80 leading-relaxed text-sm">{answerResult.explanation}</p>
          </div>
        )}

        {/* Action Button */}
        <div className="mt-auto pt-6 flex justify-end border-t border-border/20">
          {!answerResult ? (
            <button 
              onClick={submitAnswer}
              disabled={!selectedOption || loading}
              className="bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-2 min-w-35 justify-center"
            >
              {loading ? (
                <><span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin"></span> Processing</>
              ) : (
                'Submit'
              )}
            </button>
          ) : (
            <button 
              onClick={nextQuestion}
              className="bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
            >
              {answerResult.next_question ? 'Continue' : 'Complete'}
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
