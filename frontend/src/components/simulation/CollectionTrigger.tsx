interface CollectionTriggerProps {
  repoUrl?: string;
}

export function CollectionTrigger({ repoUrl }: CollectionTriggerProps) {
  const workflowUrl = repoUrl
    ? `${repoUrl}/actions/workflows/simulation.yml`
    : '#';

  return (
    <a
      href={workflowUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="
        inline-flex items-center gap-1.5 px-3 py-1.5
        bg-bg-secondary border border-border rounded-lg
        text-xs text-text-secondary font-medium
        hover:border-accent-primary hover:text-accent-primary
        transition-all
      "
    >
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 4 23 10 17 10"/>
        <polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
      </svg>
      수동 수집
    </a>
  );
}
