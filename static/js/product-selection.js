// Funcionalidade para seleção e gerenciamento de produtos e itens durante o setup

document.addEventListener('DOMContentLoaded', function() {
    console.log("[PRODUCT-SELECTION] Inicializando script de seleção de produtos");
    
    // Elementos DOM relacionados a produtos
    const productSelection = document.getElementById('productSelection');
    const productCode = document.getElementById('productCode');
    const productName = document.getElementById('productName');
    const selectedItems = document.getElementById('selectedItems');
    const itemsContainer = document.getElementById('itemsContainer');
    const noItemsMessage = document.getElementById('noItemsMessage');
    const itemsList = document.getElementById('itemsList');
    
    // Verificar se os elementos existem
    console.log("[PRODUCT-SELECTION] productSelection encontrado:", !!productSelection);
    console.log("[PRODUCT-SELECTION] productCode encontrado:", !!productCode);
    console.log("[PRODUCT-SELECTION] itemsList encontrado:", !!itemsList);
    
    // Adicionar listener para mudanças na visibilidade dos campos de abastecimento
    // Isso é necessário porque o setupFormForType em camera-scanner.js pode mostrar/esconder esses campos
    const supplyFields = document.querySelectorAll('.supply-fields');
    if (supplyFields.length > 0) {
        // Usar MutationObserver para detectar mudanças de estilo
        supplyFields.forEach(field => {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.attributeName === 'style' && 
                        field.style.display !== 'none' && 
                        productSelection) {
                        
                        console.log("[PRODUCT-SELECTION] Campo de abastecimento exibido, verificando produtos...");
                        
                        // Verificar se há produtos disponíveis
                        if (productSelection.options.length <= 1) {
                            console.log("[PRODUCT-SELECTION] Alerta: Nenhum produto encontrado para esta célula");
                            
                            // Remover alertas existentes para evitar duplicação
                            const existingAlert = document.querySelector('.product-alert-message');
                            if (existingAlert) {
                                existingAlert.remove();
                            }
                            
                            // Exibir mensagem de alerta
                            const alertMessage = document.createElement('div');
                            alertMessage.className = 'alert alert-warning mt-3 product-alert-message';
                            alertMessage.innerHTML = `
                                <i class="fa fa-exclamation-triangle me-2"></i>
                                <strong>Atenção:</strong> Nenhum produto cadastrado para esta célula.
                                Por favor, solicite a um auditor para cadastrar produtos na célula.
                            `;
                            
                            field.before(alertMessage);
                        }
                    }
                });
            });
            
            observer.observe(field, { attributes: true });
        });
    }
    
    // Variáveis globais
    let currentItems = [];
    let selectedItemsList = [];
    
    // Se o elemento de seleção de produto existir, adicionar event listener
    if (productSelection) {
        productSelection.addEventListener('change', function() {
            const selectedOption = productSelection.options[productSelection.selectedIndex];
            
            if (selectedOption.value) {
                // Atualizar código e nome do produto
                productCode.value = selectedOption.value;
                productName.value = selectedOption.getAttribute('data-name');
                
                // Carregar itens para o produto selecionado
                const cellName = document.getElementById('cellName').value;
                loadProductItems(cellName, selectedOption.value);
            } else {
                // Limpar campos
                productCode.value = '';
                productName.value = '';
                
                // Limpar itens
                itemsList.innerHTML = '';
                itemsList.style.display = 'none';
                noItemsMessage.style.display = 'block';
                selectedItemsList = [];
                updateSelectedItemsField();
            }
        });
        
        // Caso o usuário digite manualmente o código do produto
        productCode.addEventListener('blur', function() {
            const manualCode = productCode.value.trim();
            
            if (manualCode) {
                // Verificar se o código existe nas opções
                let found = false;
                for (let i = 0; i < productSelection.options.length; i++) {
                    if (productSelection.options[i].value === manualCode) {
                        productSelection.selectedIndex = i;
                        productName.value = productSelection.options[i].getAttribute('data-name');
                        found = true;
                        
                        // Carregar itens
                        const cellName = document.getElementById('cellName').value;
                        loadProductItems(cellName, manualCode);
                        break;
                    }
                }
                
                // Se não encontrou, limpar o nome e os itens
                if (!found) {
                    productName.value = '';
                    itemsList.innerHTML = '';
                    itemsList.style.display = 'none';
                    noItemsMessage.textContent = 'Código de produto não encontrado para esta célula';
                    noItemsMessage.style.display = 'block';
                    selectedItemsList = [];
                    updateSelectedItemsField();
                }
            }
        });
    }
    
    // Expor a função loadProductItems para o escopo global
    window.loadProductItems = function(cellName, productCode) {
        return loadProductItemsInternal(cellName, productCode);
    };
    
    // Função para carregar itens de um produto
    function loadProductItemsInternal(cellName, productCode) {
        if (!cellName || !productCode) {
            console.log("[PRODUCT-SELECTION] loadProductItems: cellName ou productCode vazios");
            return;
        }
        
        console.log(`[PRODUCT-SELECTION] Carregando itens para célula: ${cellName}, produto: ${productCode}`);
        
        // Verificar se os elementos existem
        if (!itemsList || !noItemsMessage) {
            console.log("[PRODUCT-SELECTION] Elementos itemsList ou noItemsMessage não encontrados");
            return;
        }
        
        // Mostrar indicador de carregamento
        itemsList.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Carregando itens...</p></div>';
        itemsList.style.display = 'block';
        noItemsMessage.style.display = 'none';
        
        fetch(`/api/product_items/${cellName}/${productCode}`)
            .then(response => {
                console.log(`[PRODUCT-SELECTION] Resposta da API product_items: status=${response.status}`);
                return response.json();
            })
            .then(data => {
                console.log(`[PRODUCT-SELECTION] Dados da API product_items:`, data);
                
                if (data.success) {
                    currentItems = data.items || [];
                    console.log(`[PRODUCT-SELECTION] Itens carregados: ${currentItems.length}`);
                    
                    if (currentItems.length > 0) {
                        displayItems(currentItems);
                    } else {
                        itemsList.innerHTML = '';
                        itemsList.style.display = 'none';
                        noItemsMessage.textContent = 'Nenhum item cadastrado para este produto';
                        noItemsMessage.style.display = 'block';
                        selectedItemsList = [];
                        updateSelectedItemsField();
                    }
                } else {
                    console.error('[PRODUCT-SELECTION] Erro ao carregar itens:', data.message);
                    itemsList.innerHTML = '';
                    itemsList.style.display = 'none';
                    noItemsMessage.textContent = 'Erro ao carregar itens do produto';
                    noItemsMessage.style.display = 'block';
                    selectedItemsList = [];
                    updateSelectedItemsField();
                }
            })
            .catch(error => {
                console.error('[PRODUCT-SELECTION] Erro na requisição de itens:', error);
                itemsList.innerHTML = '';
                itemsList.style.display = 'none';
                noItemsMessage.textContent = 'Erro ao carregar itens do produto';
                noItemsMessage.style.display = 'block';
                selectedItemsList = [];
                updateSelectedItemsField();
            });
    }
    
    // Função para exibir itens de um produto
    function displayItems(items) {
        itemsList.innerHTML = '';
        
        items.forEach(item => {
            const isChecked = selectedItemsList.some(selectedItem => 
                selectedItem.code === item.code
            );
            
            // Verificar se o item já está selecionado
            const existingItem = selectedItemsList.find(selectedItem => selectedItem.code === item.code);
            
            const itemElement = document.createElement('div');
            itemElement.className = 'col-md-12 mb-3';
            itemElement.innerHTML = `
                <div class="card bg-dark">
                    <div class="card-body p-3">
                        <div class="form-check mb-2">
                            <input class="form-check-input item-checkbox" type="checkbox" value="${item.code}" 
                                   id="item_${item.code}" data-name="${item.name}" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label" for="item_${item.code}">
                                <strong>${item.code}</strong> - ${item.name}
                            </label>
                        </div>
                        <!-- Container para informações adicionais do item se necessário no futuro -->
                    </div>
                </div>
            `;
            
            itemsList.appendChild(itemElement);
            
            // Adicionar listener para o checkbox
            const checkbox = itemElement.querySelector('.item-checkbox');
            
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    // Adicionar item à lista de selecionados
                    selectedItemsList.push({
                        code: this.value,
                        name: this.getAttribute('data-name')
                    });
                } else {
                    // Remover item da lista de selecionados
                    selectedItemsList = selectedItemsList.filter(item => 
                        item.code !== this.value
                    );
                }
                
                // Atualizar campo oculto com os itens selecionados
                updateSelectedItemsField();
            });
        });
        
        noItemsMessage.style.display = 'none';
        itemsList.style.display = 'block';
    }
    
    // Função para atualizar o campo oculto com os itens selecionados
    function updateSelectedItemsField() {
        if (selectedItems) {
            selectedItems.value = JSON.stringify(selectedItemsList);
        }
    }
});
