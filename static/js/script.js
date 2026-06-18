
document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.page-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('href').substring(1);
            
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === targetId) {
                    section.classList.add('active');
                }
            });

            if (targetId === 'historico') {
                carregarHistorico();
            } else if (targetId === 'status') {
                carregarStatus();
            }
        });
    });

    // Character Counter
    const textarea = document.getElementById('noticia-input');
    const charCount = document.getElementById('char-count');
    
    if (textarea) {
        textarea.addEventListener('input', () => {
            charCount.textContent = `${textarea.value.length}/5000`;
        });
    }

    // Analysis Logic
    const btnAnalisar = document.getElementById('btn-analisar');
    const resultContainer = document.getElementById('result-container');
    const spinner = document.getElementById('loading-spinner');
    const btnText = document.getElementById('btn-text');

    if (btnAnalisar) {
        btnAnalisar.addEventListener('click', async () => {
            const texto = textarea.value.trim();
            if (!texto) {
                alert('Por favor, insira o texto da notícia para análise.');
                return;
            }

            // UI State: Loading
            btnAnalisar.disabled = true;
            spinner.style.display = 'block';
            btnText.textContent = 'Analisando...';
            resultContainer.style.display = 'none';

            try {
                const response = await fetch('/analisar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ texto })
                });

                const data = await response.json();

                if (response.ok) {
                    exibirResultado(data);
                } else {
                    alert(data.erro || 'Erro ao processar análise.');
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro de conexão com o servidor.');
            } finally {
                btnAnalisar.disabled = false;
                spinner.style.display = 'none';
                btnText.textContent = 'Analisar notícia';
            }
        });
    }

    function exibirResultado(data) {
        const resultCard = document.getElementById('result-card');
        const badge = document.getElementById('result-badge');
        const title = document.getElementById('result-title');
        const explanation = document.getElementById('result-explanation');
        const sourceName = document.getElementById('source-name');
        const confidenceValue = document.getElementById('confidence-value');
        const confidenceProgress = document.getElementById('confidence-progress');

        // Reset classes
        badge.className = 'status-badge';
        resultCard.style.borderLeftColor = '';

        // Set content
        title.textContent = data.resultado;
        explanation.textContent = data.explicacao;
        sourceName.textContent = data.fonte;
        confidenceValue.textContent = `${Math.round(data.confianca)}%`;
        
        // Update progress circle
        const dashArray = 283;
        const dashOffset = dashArray - (dashArray * data.confianca / 100);
        confidenceProgress.style.strokeDashoffset = dashOffset;

        // Update visual based on result
        if (data.resultado === 'Verdadeiro') {
            badge.classList.add('badge-verdadeiro');
            badge.innerHTML = '✅ Verdadeiro';
            resultCard.style.borderLeftColor = 'var(--success)';
            confidenceProgress.style.stroke = 'var(--success)';
        } else if (data.resultado === 'Falso') {
            badge.classList.add('badge-falso');
            badge.innerHTML = '❌ Falso';
            resultCard.style.borderLeftColor = 'var(--danger)';
            confidenceProgress.style.stroke = 'var(--danger)';
        } else {
            badge.classList.add('badge-indeterminado');
            badge.innerHTML = '⚠️ Indeterminado';
            resultCard.style.borderLeftColor = 'var(--warning)';
            confidenceProgress.style.stroke = 'var(--warning)';
        }

        resultContainer.style.display = 'block';
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    }

    async function carregarHistorico() {
        const tbody = document.getElementById('history-body');
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Carregando histórico...</td></tr>';

        try {
            const response = await fetch('/historico');
            const data = await response.json();

            if (data.historico && data.historico.length > 0) {
                tbody.innerHTML = '';
                data.historico.forEach(item => {
                    const tr = document.createElement('tr');
                    
                    const badgeClass = item.resultado === 'Verdadeiro' ? 'badge-verdadeiro' : 
                                     (item.resultado === 'Falso' ? 'badge-falso' : 'badge-indeterminado');
                    
                    tr.innerHTML = `
                        <td>${item.data_hora}</td>
                        <td><div class="history-text" title="${item.texto}">${item.texto}</div></td>
                        <td><span class="status-badge ${badgeClass}">${item.resultado}</span></td>
                        <td>${item.confianca ? item.confianca + '%' : '-'}</td>
                        <td><div class="history-source"><i class="fas fa-database"></i> ${item.fonte}</div></td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhum registro encontrado.</td></tr>';
            }
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--danger)">Erro ao carregar histórico.</td></tr>';
        }
    }

    async function carregarStatus() {
        const statusGrid = document.getElementById('status-grid');
        statusGrid.innerHTML = '<div style="grid-column: 1/-1; text-align:center">Verificando status dos serviços...</div>';

        try {
            const response = await fetch('/status');
            const data = await response.json();

            if (data.servicos) {
                statusGrid.innerHTML = '';
                
                // Renderizar cards de serviços
                data.servicos.forEach(servico => {
                    const card = document.createElement('div');
                    card.className = 'status-item-card';
                    
const icon = servico.nome.includes('Google') ? 'fa-search' : 
	                                (servico.nome.includes('News') ? 'fa-newspaper' : 
	                                (servico.nome.includes('Sistema') ? 'fa-shield-alt' : 'fa-database'));
                    
                    card.innerHTML = `
                        <div class="status-icon"><i class="fas ${icon}"></i></div>
                        <h3>${servico.nome}</h3>
                        <div class="status-indicator">
                            <span class="dot ${servico.online ? 'dot-online' : 'dot-offline'}"></span>
                            ${servico.status}
                        </div>
                        <p style="color: var(--text-secondary); font-size: 0.9rem;">${servico.descricao}</p>
                    `;
                    statusGrid.appendChild(card);
                });
                
                // Renderizar card de dataset
                if (data.dataset) {
                    const datasetCard = document.createElement('div');
                    datasetCard.className = 'status-item-card';
                    datasetCard.style.gridColumn = '1 / -1';
                    datasetCard.innerHTML = `
                        <div class="status-icon"><i class="fas fa-database"></i></div>
                        <h3>Dataset Consolidado</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; font-size: 0.9rem;">
                            <div>
                                <strong>Total:</strong> ${data.dataset.tamanho} registros
                            </div>
                            <div>
                                <strong>Verdadeiros:</strong> ${data.dataset.verdadeiros}
                            </div>
                            <div>
                                <strong>Falsos:</strong> ${data.dataset.falsos}
                            </div>
                            <div>
                                <strong>Confiança Média:</strong> ${data.dataset.confianca_media.toFixed(2)}%
                            </div>
                        </div>
                    `;
                    statusGrid.appendChild(datasetCard);
                }
                
	                // Renderizar card de última atualização
	                if (data.ultima_atualizacao) {
	                    const retrainCard = document.createElement('div');
	                    retrainCard.className = 'status-item-card';
	                    retrainCard.style.gridColumn = '1 / -1';
	                    retrainCard.innerHTML = `
		                        <div class="status-icon"><i class="fas fa-brain"></i></div>
		                        <h3>Último Retreinamento (ML)</h3>
		                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; font-size: 0.9rem;">
		                            <div>
		                                <strong>Data:</strong> ${data.ultima_atualizacao.data}
		                            </div>
		                            <div>
		                                <strong>Acurácia:</strong> ${(data.ultima_atualizacao.accuracy * 100).toFixed(2)}%
		                            </div>
		                            <div>
		                                <strong>F1-Score:</strong> ${data.ultima_atualizacao.f1_score.toFixed(4)}
		                            </div>
		                        </div>
	                    `;
	                    statusGrid.appendChild(retrainCard);
	                }
            }
        } catch (error) {
            statusGrid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; color:var(--danger)">Erro ao verificar status.</div>';
        }
    }
});
