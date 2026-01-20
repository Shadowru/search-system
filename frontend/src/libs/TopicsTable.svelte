<script>
  
  export let topics = []; 
  export let loading = false;
  export let error = null;

  // Локальные фильтры и сортировка остаются здесь
  let searchTerm = "";
  let roleFilter = "ALL"; 
  let sortColumn = "topic_name";
  let sortDirection = 1;

  // Реактивность для фильтрации (работает с пришедшими topics)
  $: processedTopics = topics
    .filter((t) => {
      const matchText = 
        t.topic_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (t.jira_key && t.jira_key.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchRole = roleFilter === "ALL" || t.role.toUpperCase() === roleFilter;

      return matchText && matchRole;
    })
    .sort((a, b) => {
      const valA = (a[sortColumn] || "").toString().toLowerCase();
      const valB = (b[sortColumn] || "").toString().toLowerCase();
      
      if (valA < valB) return -1 * sortDirection;
      if (valA > valB) return 1 * sortDirection;
      return 0;
    });

  function handleSort(column) {
    if (sortColumn === column) {
      sortDirection *= -1;
    } else {
      sortColumn = column;
      sortDirection = 1;
    }
  }
</script>

<div class="topics-container">
    {#if loading}
        <div class="loading">Загрузка топиков...</div>
    {:else if error}
        <div class="error">Ошибка: {error}</div>
    {:else if topics.length === 0}
        <div class="empty">Нет связанных топиков</div>
    {:else}
        <!-- Панель управления -->
        <div class="controls">
            <input
                type="text"
                placeholder="Поиск топика..."
                bind:value={searchTerm}
                class="search-input"
            />

            <select bind:value={roleFilter} class="role-select">
                <option value="ALL">Все роли</option>
                <option value="PRODUCER">Producer</option>
                <option value="CONSUMER">Consumer</option>
            </select>
        </div>

        <!-- Таблица -->
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th
                            on:click={() => handleSort("topic_name")}
                            class:active={sortColumn === "topic_name"}
                        >
                            Topic Name {sortColumn === "topic_name"
                                ? sortDirection === 1
                                    ? "▲"
                                    : "▼"
                                : ""}
                        </th>
                        <th
                            on:click={() => handleSort("role")}
                            class:active={sortColumn === "role"}
                        >
                            Role {sortColumn === "role"
                                ? sortDirection === 1
                                    ? "▲"
                                    : "▼"
                                : ""}
                        </th>
                        <th
                            on:click={() => handleSort("jira_key")}
                            class:active={sortColumn === "jira_key"}
                        >
                            Jira {sortColumn === "jira_key"
                                ? sortDirection === 1
                                    ? "▲"
                                    : "▼"
                                : ""}
                        </th>
                        <th
                            on:click={() => handleSort("consumer_group")}
                            class:active={sortColumn === "consumer_group"}
                        >
                            CG {sortColumn === "consumer_group"
                                ? sortDirection === 1
                                    ? "▲"
                                    : "▼"
                                : ""}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {#each processedTopics as topic}
                        <tr>
                            <td class="topic-name" title={topic.topic_name}
                                >{topic.topic_name}</td
                            >
                            <td>
                                <span class="badge {topic.role.toLowerCase()}"
                                    >{topic.role}</span
                                >
                            </td>
                            <td>
                                {#if topic.jira_key}
                                    <a
                                        href={`https://jira.example.com/browse/${topic.jira_key}`}
                                        target="_blank">{topic.jira_key}</a
                                    >
                                {:else}
                                    -
                                {/if}
                            </td>
                            <td
                                class="cg-cell"
                                title={topic.consumer_group || ""}
                            >
                                {topic.consumer_group || "-"}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
        <div class="count">Найдено: {processedTopics.length}</div>
    {/if}
</div>

<style>
    .topics-container {
        margin-top: 1rem;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        animation: fadeIn 0.3s ease;
    }

    .controls {
        display: flex;
        gap: 10px;
        margin-bottom: 1rem;
    }

    .search-input {
        flex: 1;
        padding: 8px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        font-size: 0.9rem;
    }

    .role-select {
        padding: 8px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: white;
    }

    .table-wrapper {
        overflow-x: auto;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
        background: white;
    }

    th {
        background: #f1f5f9;
        padding: 10px;
        text-align: left;
        cursor: pointer;
        user-select: none;
        font-weight: 600;
        color: #475569;
        border-bottom: 2px solid #e2e8f0;
    }

    th:hover {
        background: #e2e8f0;
    }

    td {
        padding: 8px 10px;
        border-bottom: 1px solid #f1f5f9;
        color: #334155;
    }

    tr:last-child td {
        border-bottom: none;
    }

    tr:hover {
        background-color: #f8fafc;
    }

    .topic-name {
        font-family: monospace;
        font-weight: 500;
        max-width: 250px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .cg-cell {
        max-width: 150px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: #64748b;
        font-size: 0.85rem;
    }

    .badge {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .badge.producer {
        background-color: #dcfce7;
        color: #166534;
    }

    .badge.consumer {
        background-color: #dbeafe;
        color: #1e40af;
    }

    .count {
        margin-top: 8px;
        font-size: 0.8rem;
        color: #64748b;
        text-align: right;
    }

    .loading,
    .empty,
    .error {
        text-align: center;
        padding: 1rem;
        color: #64748b;
    }

    .error {
        color: #ef4444;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
