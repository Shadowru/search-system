<script>
  export let system;
  
  // Функция для определения цвета бейджика в зависимости от релевантности
  function getScoreColor(score) {
    if (score > 80) return '#10b981'; // Green
    if (score > 60) return '#f59e0b'; // Orange
    return '#6b7280'; // Gray
  }
</script>

<div class="card">
  <div class="header">
    <h3>{system.product_name}</h3>
    <span class="score" style="background-color: {getScoreColor(system.search_score)}">
      {Math.round(system.search_score)}%
    </span>
  </div>

  <p class="description">
    {system.description || "Описание отсутствует"}
  </p>

  <div class="meta">
    {#if system.owner_name}
      <div class="owner">
        <strong>Владелец:</strong> {system.owner_name}
        {#if system.owner_telegram}
           <a href="https://t.me/{system.owner_telegram.replace('@', '')}" target="_blank" class="tg-link">(@{system.owner_telegram.replace('@', '')})</a>
        {/if}
      </div>
    {/if}
  </div>

  <div class="links">
    {#if system.wiki_url}
      <a href={system.wiki_url} target="_blank" class="btn wiki">Wiki</a>
    {/if}
    {#if system.jira_url}
      <a href={system.jira_url} target="_blank" class="btn jira">Jira</a>
    {/if}
    {#if system.repo_url}
      <a href={system.repo_url} target="_blank" class="btn repo">Repo</a>
    {/if}
  </div>
</div>

<style>
  .card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 0.5rem;
  }
  h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #111827;
  }
  .score {
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: bold;
  }
  .description {
    color: #4b5563;
    font-size: 0.95rem;
    margin-bottom: 1rem;
    line-height: 1.5;
  }
  .meta {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 1rem;
  }
  .tg-link {
    color: #3b82f6;
    text-decoration: none;
  }
  .links {
    display: flex;
    gap: 0.5rem;
  }
  .btn {
    text-decoration: none;
    padding: 0.4rem 0.8rem;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.8; }
  .wiki { background-color: #0052CC; color: white; }
  .jira { background-color: #2684FF; color: white; }
  .repo { background-color: #24292e; color: white; }
</style>