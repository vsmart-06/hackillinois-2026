const SemflowLogo = ({ size = 28 }: { size?: number }) => {
  const fontSize = size * 0.7;
  return (
    <span
      style={{ fontSize: `${fontSize}px`, lineHeight: 1 }}
      className="font-logo font-semibold tracking-tight text-primary-foreground select-none"
    >
      Semflow
    </span>
  );
};

export default SemflowLogo;
