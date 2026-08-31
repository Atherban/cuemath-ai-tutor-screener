interface EndInterviewButtonProps {
  onClick: () => void;
  disabled: boolean;
}

export function EndInterviewButton({ onClick, disabled }: EndInterviewButtonProps) {
  return (
    <div className="interview__end">
      <button
        className="btn btn--danger-ghost btn--sm"
        onClick={onClick}
        disabled={disabled}
        aria-label="End interview"
      >
        End Interview
      </button>
    </div>
  );
}