<script>
  import SystemCard from './libs/SystemCard.svelte';
  
  let query = "";
  let results = [];
  let isLoading = false;
  let error = null;
  let hasSearched = false;

  async function handleSearch() {
    if (!query.trim()) return;
    
    isLoading = true;
    error = null;
    results = [];
    hasSearched = true;

    try {
      // Запрос к твоему локальному API
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`);
      
      if (!response.ok) {
        throw new Error('Ошибка сервера');
      }
      
      results = await response.json();
    } catch (err) {
      error = "Не удалось загрузить данные. Убедитесь, что backend запущен.";
      console.error(err);
    } finally {
      isLoading = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }
</script>

<main>
  <div class="container">
    <header>
      <h1>🔍 База Знаний Систем</h1>
      <p>Найдите ответственного, документацию или репозиторий</p>
    </header>

    <div class="search-box">
      <input 
        type="text" 
        bind:value={query} 
        on:keydown={handleKeydown}
        placeholder="Например: зачисление в сад..." 
      />
      <button on:click={handleSearch} disabled={isLoading}>
        {isLoading ? 'Поиск...' : 'Найти'}
      </button>
    </div>

    <div class="results-area">
      {#if error}
        <div class="error">{error}</div>
      {/if}

      {#if !isLoading && hasSearched && results.length === 0 && !error}
        <div class="empty-state">Ничего не найдено 😔 Попробуйте другой запрос.</div>
      {/if}

      <div class="grid">
        {#each results as system (system.id)}
          <SystemCard {system} />
        {/each}
      </div>
    </div>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #f3f4f6;
    color: #1f2937;
  }

  main {
    padding: 2rem 1rem;
  }

  .container {
    max-width: 800px;
    margin: 0 auto;
  }

  header {
    text-align: center;
    margin-bottom: 2rem;
  }

  h1 {
    margin-bottom: 0.5rem;
    color: #111827;
  }

  p {
    color: #6b7280;
  }

  .search-box {
    display: flex;
    gap: 10px;
    margin-bottom: 2rem;
    background: white;
    padding: 1rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  input {
    flex: 1;
    padding: 12px 16px;
    font-size: 1rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    outline: none;
    transition: border-color 0.2s;
  }

  input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  button {
    padding: 0 24px;
    background-color: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  button:hover {
    background-color: #2563eb;
  }

  button:disabled {
    background-color: #93c5fd;
    cursor: not-allowed;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .error {
    background-color: #fee2e2;
    color: #991b1b;
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
  }

  .empty-state {
    text-align: center;
    color: #6b7280;
    margin-top: 2rem;
  }
</style>