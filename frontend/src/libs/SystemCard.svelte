<script>
  import TopicsTable from "./TopicsTable.svelte";
  export let system;

  let isExpanded = false;
  let summary = null;
  let isLoadingSummary = false;

  let showTopics = false;
  let topicsData = [];      // Храним данные здесь
  let topicsLoading = false;
  let topicsError = null;
  let topicsLoaded = false; // Флаг, чтобы не грузить повторно

  // Цвета для статусов
  function getStatusClass(status) {
    if (!status) return "status-gray";
    const s = status.toLowerCase();
    if (s.includes("эксплуатация") || s.includes("prod")) return "status-green";
    if (s.includes("создание") || s.includes("dev")) return "status-blue";
    if (s.includes("вывод") || s.includes("архив")) return "status-red";
    return "status-gray";
  }

  async function toggleSummary() {
    isExpanded = !isExpanded;

    if (isExpanded && !summary) {
      isLoadingSummary = true;
      try {
        const token = localStorage.getItem("token");
        const res = await fetch(`/api/summarize/${system.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          summary = data.summary;
        } else {
          summary = "Ошибка загрузки справки.";
        }
      } catch (e) {
        summary = "Не удалось связаться с сервером.";
      } finally {
        isLoadingSummary = false;
      }
    }
  }
  async function toggleTopics() {
    showTopics = !showTopics;

    // Если открываем и данные еще не загружены — грузим
    if (showTopics && !topicsLoaded) {
        topicsLoading = true;
        topicsError = null;
        
        try {
            const token = localStorage.getItem("token");
            // Используем system.code или system.id
            const code = system.product_code;// || system.id; 
            
            const res = await fetch(`/api/systems/${encodeURIComponent(code)}/topics`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (res.status === 401) {
                throw new Error("Нужна авторизация");
            }
            if (!res.ok) throw new Error("Ошибка загрузки");

            topicsData = await res.json();
            topicsLoaded = true; // Запоминаем, что загрузили
        } catch (e) {
            topicsError = e.message;
        } finally {
            topicsLoading = false;
        }
    }
  }
</script>

<div class="card">
  <div class="header">
    <div class="title-group">
      <h3>{system.product_name}</h3>
      {#if system.status}
        <span class="status-badge {getStatusClass(system.status)}">
          {system.status}
        </span>
      {/if}
    </div>
    <span class="score">{Math.round(system.search_score)}%</span>
  </div>

  <p class="description">
    {system.description || "Описание отсутствует"}
  </p>

  <!-- Кнопка AI Summary -->
  {#if system.has_wiki_content}
    <div class="ai-section">
      <button class="ai-btn" on:click={toggleSummary}>
        {#if isExpanded}
          🔽 Скрыть справку
        {:else}
          ✨ AI Справка (Ollama)
        {/if}
      </button>

      {#if isExpanded}
        <div class="summary-content">
          {#if isLoadingSummary}
            <div class="loading">Обработка документации ...</div>
          {:else}
            <p>{summary}</p>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <div class="topics-section">
    <button class="action-btn topics-btn" on:click={toggleTopics}>
      {#if showTopics}
        🔽 Скрыть топики Kafka
      {:else}
        📦 Топики Kafka
      {/if}
    </button>

    {#if showTopics}
      <!-- Передаем данные и состояние загрузки в компонент -->
      <TopicsTable 
        topics={topicsData} 
        loading={topicsLoading} 
        error={topicsError} 
      />
    {/if}
  </div>

  <div class="meta">
    {#if system.owner_name}
      <div class="owner">
        <strong>Владелец:</strong>
        {system.owner_name}
        {#if system.owner_telegram}
          <a
            href="https://t.me/{system.owner_telegram.replace('@', '')}"
            target="_blank">(@{system.owner_telegram.replace("@", "")})</a
          >
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
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    margin-bottom: 0.5rem;
  }
  .title-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #111827;
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    width: fit-content;
  }
  .status-green {
    background: #d1fae5;
    color: #065f46;
  }
  .status-blue {
    background: #dbeafe;
    color: #1e40af;
  }
  .status-red {
    background: #fee2e2;
    color: #991b1b;
  }
  .status-gray {
    background: #f3f4f6;
    color: #374151;
  }

  .score {
    background: #10b981;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: bold;
    height: fit-content;
  }
  .description {
    color: #4b5563;
    margin-bottom: 1rem;
  }
  .topics-section { margin-bottom: 1rem; }
  .action-btn {
    background: none; padding: 5px 10px; border-radius: 6px;
    cursor: pointer; font-size: 0.85rem; transition: all 0.2s; margin-right: 10px;
  }
  .topics-btn { border: 1px solid #059669; color: #059669; }
  .topics-btn:hover { background: #ecfdf5; }


  /* AI Section Styles */
  .ai-section {
    margin-bottom: 1rem;
  }
  .ai-btn {
    background: none;
    border: 1px solid #8b5cf6;
    color: #7c3aed;
    padding: 5px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    border: 1px solid #8b5cf6;
    color: #7c3aed;
    transition: all 0.2s;
  }
  .ai-btn:hover {
    background: #f5f3ff;
  }
  .summary-content {
    margin-top: 10px;
    padding: 10px;
    background: #f5f3ff;
    border-radius: 6px;
    border-left: 3px solid #8b5cf6;
    font-size: 0.9rem;
    color: #4c1d95;
  }
  .loading {
    font-style: italic;
    color: #6b7280;
  }

  .meta {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 1rem;
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
    color: white;
  }
  .wiki {
    background-color: #0052cc;
  }
  .jira {
    background-color: #2684ff;
  }
  .repo {
    background-color: #24292e;
  }
</style>
