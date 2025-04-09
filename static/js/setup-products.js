// Script para carregar produtos da célula via API quando o QR code é escaneado
document.addEventListener('DOMContentLoaded', function() {
    console.log("[SETUP-PRODUCTS] Inicializando carregamento de produtos para a página de setup");
    
    // Elementos DOM relacionados a produtos
    const productSelection = document.getElementById('productSelection');
    const cellNameInput = document.getElementById('cellName');
    const setupTypeInput = document.getElementById('setupType');
    
    // Obter o QR code da URL
    const qrcodeValue = new URLSearchParams(window.location.search).get('qrcode');
    
    // Verificar se os elementos existem
    console.log("[SETUP-PRODUCTS] productSelection encontrado:", !!productSelection);
    console.log("[SETUP-PRODUCTS] cellNameInput encontrado:", !!cellNameInput);
    console.log("[SETUP-PRODUCTS] setupTypeInput encontrado:", !!setupTypeInput);
    console.log("[SETUP-PRODUCTS] QR code na URL:", qrcodeValue);
    
    // Verificar se estamos na página de supply e se precisamos carregar produtos
    function shouldLoadProducts() {
        if (!productSelection) {
            console.log("[SETUP-PRODUCTS] Dropdown de produtos não encontrado no DOM");
            return false;
        }
        
        if (!setupTypeInput || setupTypeInput.value !== 'supply') {
            console.log("[SETUP-PRODUCTS] Não é uma operação de abastecimento (supply)");
            return false;
        }
        
        if (productSelection.options.length > 1) {
            console.log("[SETUP-PRODUCTS] Produtos já estão carregados no dropdown");
            return false;
        }
        
        return true;
    }
    
    // Função para carregar produtos via API
    function loadCellProducts() {
        // Obter o nome da célula
        let cellName = cellNameInput?.value || '';
        
        // Se não tivermos o valor do QR code nem o nome da célula, não podemos continuar
        if (!qrcodeValue && !cellName) {
            console.log("[SETUP-PRODUCTS] Nem QR code nem nome da célula foram fornecidos");
            return;
        }
        
        // Mostrar indicador de carregamento
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'text-center my-3 product-loading';
        loadingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div><p class="mt-2">Carregando produtos...</p>';
        
        // Inserir o indicador próximo ao dropdown
        if (productSelection && productSelection.parentElement) {
            // Remover qualquer indicador existente
            const existingIndicator = document.querySelector('.product-loading');
            if (existingIndicator) existingIndicator.remove();
            
            productSelection.parentElement.appendChild(loadingIndicator);
        }
        
        console.log("[SETUP-PRODUCTS] Iniciando carregamento de produtos");
        
        // Se temos apenas o QR code, primeiro precisamos obter o nome da célula
        if (!cellName && qrcodeValue) {
            console.log(`[SETUP-PRODUCTS] Buscando nome da célula para QR code: ${qrcodeValue}`);
            
            fetch(`/api/get_cell_name/${qrcodeValue}`)
                .then(response => {
                    console.log(`[SETUP-PRODUCTS] Resposta da API get_cell_name: status=${response.status}`);
                    return response.json();
                })
                .then(data => {
                    console.log(`[SETUP-PRODUCTS] Dados da API get_cell_name:`, data);
                    
                    if (data.success) {
                        cellName = data.cell_name;
                        console.log(`[SETUP-PRODUCTS] QR code ${qrcodeValue} corresponde à célula ${cellName}`);
                        
                        if (cellNameInput && !cellNameInput.value) {
                            cellNameInput.value = cellName;
                        }
                        
                        // Agora que temos o nome da célula, carregar os produtos
                        fetchProductsForCell(cellName);
                    } else {
                        console.error("[SETUP-PRODUCTS] QR code não encontrado:", data.message);
                        showNoProductsWarning("QR code não encontrado ou não está registrado no sistema.");
                        loadingIndicator.remove();
                    }
                })
                .catch(error => {
                    console.error("[SETUP-PRODUCTS] Erro ao obter nome da célula:", error);
                    showNoProductsWarning("Erro de conexão ao buscar informações da célula.");
                    loadingIndicator.remove();
                });
        } else {
            // Já temos o nome da célula, podemos ir direto para a busca de produtos
            fetchProductsForCell(cellName);
        }
        
        // Função para buscar produtos para uma célula
        function fetchProductsForCell(cellName) {
            console.log(`[SETUP-PRODUCTS] Buscando produtos para célula: ${cellName}`);
            
            fetch(`/api/cell_products/${cellName}`)
                .then(response => {
                    console.log(`[SETUP-PRODUCTS] Resposta da API cell_products: status=${response.status}`);
                    return response.json();
                })
                .then(productsData => {
                    console.log(`[SETUP-PRODUCTS] Dados da API cell_products:`, productsData);
                    loadingIndicator.remove();
                    
                    if (productsData.success && productsData.products && productsData.products.length > 0) {
                        console.log(`[SETUP-PRODUCTS] ${productsData.products.length} produtos encontrados para célula ${cellName}`);
                        
                        // Mostrar mensagem de sucesso temporária
                        const successMsg = document.createElement('div');
                        successMsg.className = 'alert alert-success mt-2 mb-3 product-success-message';
                        successMsg.innerHTML = `<i class="fa fa-check-circle me-2"></i> ${productsData.products.length} produtos carregados com sucesso!`;
                        
                        if (productSelection && productSelection.parentElement) {
                            productSelection.parentElement.appendChild(successMsg);
                            setTimeout(() => {
                                successMsg.remove();
                            }, 3000);
                        }
                        
                        updateProductDropdown(productsData.products);
                    } else {
                        console.log("[SETUP-PRODUCTS] Nenhum produto retornado pela API");
                        showNoProductsWarning("Nenhum produto encontrado para esta célula");
                    }
                })
                .catch(error => {
                    console.error("[SETUP-PRODUCTS] Erro ao carregar produtos:", error);
                    loadingIndicator.remove();
                    showNoProductsWarning("Erro de conexão ao buscar produtos da célula");
                });
        }
    }
    
    // Função para atualizar o dropdown de produtos
    function updateProductDropdown(products) {
        if (!productSelection) {
            console.error("[SETUP-PRODUCTS] Elemento productSelection não encontrado");
            return;
        }
        
        console.log("[SETUP-PRODUCTS] Atualizando dropdown com", products.length, "produtos");
        
        // Manter apenas a primeira opção (Selecione um produto)
        while (productSelection.options.length > 1) {
            productSelection.remove(1);
        }
        
        // Adicionar cada produto ao dropdown
        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.code;
            option.text = `${product.code} - ${product.name}`;
            option.setAttribute('data-name', product.name);
            productSelection.appendChild(option);
            console.log(`[SETUP-PRODUCTS] Adicionado produto: ${product.code} - ${product.name}`);
        });
        
        // Remover qualquer aviso existente
        const existingAlert = document.querySelector('.product-alert-message');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // Se estamos na tela de setup e o tipo é 'supply', atualizar a visibilidade dos campos
        const setupType = setupTypeInput?.value;
        if (setupType === 'supply') {
            console.log("[SETUP-PRODUCTS] Operação de abastecimento (supply) - mostrando campos");
            const supplyFields = document.querySelectorAll('.supply-fields');
            supplyFields.forEach(field => {
                field.style.display = 'block';
            });
        }
        
        // Atualizar o evento de seleção para carregar itens do produto selecionado
        if (typeof loadProductItems === 'function') {
            console.log("[SETUP-PRODUCTS] Configurando evento para carregar itens ao selecionar produto");
            productSelection.addEventListener('change', function() {
                const selectedProductCode = this.value;
                if (selectedProductCode) {
                    loadProductItems(cellNameInput.value, selectedProductCode);
                }
            });
        } else {
            console.log("[SETUP-PRODUCTS] Função loadProductItems não encontrada, não será possível carregar itens automaticamente");
        }
    }
    
    // Função para mostrar aviso de que não há produtos
    function showNoProductsWarning(message = "Nenhum produto cadastrado para esta célula") {
        // Verificar se já existe um alerta
        const existingAlert = document.querySelector('.product-alert-message');
        if (existingAlert) {
            existingAlert.innerHTML = `
                <i class="fa fa-exclamation-triangle me-2"></i>
                <strong>Atenção:</strong> ${message}.
                Por favor, solicite a um auditor para cadastrar produtos na célula.
            `;
            return;
        }
        
        // Criar alerta
        const alertMessage = document.createElement('div');
        alertMessage.className = 'alert alert-warning mt-3 product-alert-message';
        alertMessage.innerHTML = `
            <i class="fa fa-exclamation-triangle me-2"></i>
            <strong>Atenção:</strong> ${message}.
            Por favor, solicite a um auditor para cadastrar produtos na célula.
        `;
        
        // Inserir o alerta no formulário
        if (productSelection && productSelection.parentElement) {
            productSelection.parentElement.appendChild(alertMessage);
        } else {
            const supplyFields = document.querySelectorAll('.supply-fields');
            if (supplyFields.length > 0) {
                supplyFields[0].before(alertMessage);
            }
        }
    }
    
    // Tentar carregar produtos após garantir que o restante da página esteja carregado
    // Primeiro verificar se estamos na seção de supply form
    function checkAndLoadProducts() {
        console.log("[SETUP-PRODUCTS] Verificando se devemos carregar produtos...");
        
        if (shouldLoadProducts()) {
            console.log("[SETUP-PRODUCTS] Iniciando carregamento de produtos");
            loadCellProducts();
        } else {
            console.log("[SETUP-PRODUCTS] Não é necessário carregar produtos neste momento");
        }
    }
    
    // Verificar inicialmente e configurar verificação periódica
    // (isso é útil pois o formulário pode ficar oculto inicialmente)
    checkAndLoadProducts();
    
    // Verificar a cada 1 segundo por 5 segundos (em caso de carregamento atrasado de DOM)
    let checkCount = 0;
    const checkInterval = setInterval(() => {
        checkCount++;
        checkAndLoadProducts();
        
        if (checkCount >= 5) {
            clearInterval(checkInterval);
        }
    }, 1000);
    
    // Não adicionar botão de recarregar produtos
    
    // Monitorar mudanças no tipo de setup
    if (setupTypeInput) {
        setupTypeInput.addEventListener('change', function() {
            console.log(`[SETUP-PRODUCTS] Tipo de setup alterado para: ${this.value}`);
            if (this.value === 'supply') {
                checkAndLoadProducts();
            }
        });
    }
    
    // Adicionando eventos de debug para compreender melhor o fluxo
    if (productSelection) {
        // Monitorar quando o productSelection é modificado
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    console.log(`[SETUP-PRODUCTS] Dropdown de produtos modificado. Opções atuais: ${productSelection.options.length}`);
                }
            });
        });
        
        observer.observe(productSelection, { childList: true });
    }
});
