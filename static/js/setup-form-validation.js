// Script para validação do formulário de setup e habilitação do botão de envio
// Criar objeto global para permitir acesso externo a funções específicas
var setupFormValidation = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log("[SETUP-VALIDATION] Inicializando validação do formulário de setup");
    
    // Elementos do formulário
    const setupForm = document.getElementById('setupForm');
    const submitButton = document.getElementById('submitSetupBtn');
    const finalizeButton = document.getElementById('finalizeButton'); // Botão usado no modo formulário
    const setupType = document.getElementById('setupType');
    const orderNumber = document.getElementById('orderNumber');
    const supplierName = document.getElementById('supplierName');
    const supplierUserContainer = document.getElementById('supplierUserContainer');
    const photoInput = document.getElementById('photoInput');
    const photoData = document.getElementById('photoData');
    const verificationCheck = document.getElementById('verificationCheck');
    const productSelection = document.getElementById('productSelection');
    const productCode = document.getElementById('productCode');
    const productName = document.getElementById('productName');
    const selectedItems = document.getElementById('selectedItems');
    
    // Estado de validação
    let formValidationState = {
        orderNumber: false,
        supplierName: false,
        photo: false,
        verification: false,
        product: true,  // Por padrão verdadeiro, só é necessário para supply
        items: true     // Por padrão verdadeiro, só é necessário para supply
    };
    
    if (!setupForm || !submitButton) {
        console.log("[SETUP-VALIDATION] Formulário ou botão de envio não encontrado");
        return;
    }
    
    // Desabilitar o botão inicialmente
    submitButton.disabled = true;
    
    // Função para verificar se todos os campos obrigatórios estão preenchidos
    function validateForm() {
        console.log("[SETUP-VALIDATION] Validando formulário...");
        
        // Verificar o tipo de setup (supply ou removal)
        const isSupplyType = setupType.value === 'supply';
        
        // Para abastecimento (supply), também validar produto e itens
        if (isSupplyType) {
            // Produto é obrigatório
            formValidationState.product = !!productCode.value && !!productName.value;
            
            // Validar se os itens do produto estão completos
            validateSelectedItems();
        } else {
            // Para retirada (removal), esses campos não são obrigatórios
            formValidationState.product = true;
            formValidationState.items = true;
        }
        
        // Verificar todos os campos obrigatórios
        const allValid = Object.values(formValidationState).every(value => value === true);
        
        // Log do estado da validação
        console.log("[SETUP-VALIDATION] Estado da validação:", formValidationState);
        console.log("[SETUP-VALIDATION] Todos os campos válidos?", allValid);
        
        // Atualizar estado do botão de envio
        submitButton.disabled = !allValid;
        
        // Adicionar ou remover classe para destacar o botão quando estiver habilitado
        if (allValid) {
            submitButton.classList.add('btn-success');
            submitButton.classList.remove('btn-secondary');
        } else {
            submitButton.classList.remove('btn-success');
            submitButton.classList.add('btn-secondary');
        }
        
        return allValid;
    }
    
    // Validar itens selecionados para garantir que todos os POs foram preenchidos
    function validateSelectedItems() {
        if (!isSupplyType()) return true;
        
        try {
            // Verificar se temos itens selecionados
            const items = selectedItems.value ? JSON.parse(selectedItems.value) : [];
            
            if (items.length === 0) {
                // Nenhum item selecionado
                formValidationState.items = false;
                console.log("[SETUP-VALIDATION] Nenhum item selecionado");
                return false;
            }
            
            // Verificar se todos os itens têm PO de fornecedor
            const allItemsHavePO = items.every(item => item.supplierPO && item.supplierPO.trim() !== '');
            
            formValidationState.items = allItemsHavePO;
            
            console.log("[SETUP-VALIDATION] Itens selecionados:", items.length);
            console.log("[SETUP-VALIDATION] Todos os itens têm PO?", allItemsHavePO);
            
            return allItemsHavePO;
        } catch (e) {
            console.error("[SETUP-VALIDATION] Erro ao verificar itens:", e);
            formValidationState.items = false;
            return false;
        }
    }
    
    // Verificar se estamos em uma operação de abastecimento
    function isSupplyType() {
        return setupType && setupType.value === 'supply';
    }
    
    // Adicionar listeners para os campos obrigatórios
    
    // Ordem de produção
    if (orderNumber) {
        orderNumber.addEventListener('input', function() {
            formValidationState.orderNumber = !!this.value.trim();
            validateForm();
        });
    }
    
    // Nome do abastecedor (se não for perfil de abastecedor)
    if (supplierName) {
        supplierName.addEventListener('input', function() {
            formValidationState.supplierName = !!this.value.trim();
            validateForm();
        });
    }
    
    // Se for perfil de abastecedor, já podemos considerar o nome como válido
    if (supplierUserContainer && supplierUserContainer.style.display !== 'none') {
        formValidationState.supplierName = true;
    }
    
    // Foto do setup
    if (photoInput) {
        photoInput.addEventListener('change', function() {
            formValidationState.photo = this.files.length > 0;
            validateForm();
        });
        
        // Verificar também quando os dados da foto são atualizados (via data URL)
        if (photoData) {
            const photoDataObserver = new MutationObserver(function() {
                formValidationState.photo = !!photoData.value;
                validateForm();
            });
            
            photoDataObserver.observe(photoData, { attributes: true });
        }
    }
    
    // Verificação do setup
    if (verificationCheck) {
        verificationCheck.addEventListener('change', function() {
            formValidationState.verification = this.checked;
            validateForm();
        });
    }
    
    // Seleção de produto (apenas para abastecimento)
    if (productSelection) {
        productSelection.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            formValidationState.product = !!selectedOption.value;
            validateForm();
        });
    }
    
    // Atualização de código de produto manualmente
    if (productCode) {
        productCode.addEventListener('input', function() {
            formValidationState.product = !!this.value.trim() && !!productName.value.trim();
            validateForm();
        });
    }
    
    // Atualização de nome de produto
    if (productName) {
        productName.addEventListener('input', function() {
            formValidationState.product = !!this.value.trim() && !!productCode.value.trim();
            validateForm();
        });
    }
    
    // Observar mudanças nos itens selecionados
    if (selectedItems) {
        selectedItems.addEventListener('change', function() {
            validateSelectedItems();
            validateForm();
        });
        
        // Verificar também alterações via JavaScript
        const selectedItemsObserver = new MutationObserver(function() {
            validateSelectedItems();
            validateForm();
        });
        
        selectedItemsObserver.observe(selectedItems, { attributes: true });
        
        // Verificar eventos de entrada na lista de itens para detectar quando os POs são preenchidos
        document.addEventListener('input', function(e) {
            if (e.target && e.target.classList.contains('supplier-po-input')) {
                // Esperar um pouco para que o valor seja atualizado no campo selectedItems
                setTimeout(function() {
                    validateSelectedItems();
                    validateForm();
                }, 100);
            }
        });
    }
    
    // Monitorar mudanças no tipo de setup
    if (setupType) {
        setupType.addEventListener('change', function() {
            // Atualizar a validação quando o tipo de setup mudar
            validateForm();
        });
    }
    
    // Validar o formulário ao carregar a página
    setTimeout(validateForm, 500);
    
    // Exportar funções para o objeto global
    setupFormValidation = {
        // Função para atualizar a validação da foto
        updatePhotoValidation: function(isValid) {
            console.log("[SETUP-VALIDATION] Atualizando validação da foto:", isValid);
            formValidationState.photo = isValid;
            validateForm();
            
            // Se temos o botão finalizeButton, atualizar seu estado também
            if (finalizeButton) {
                const allValid = Object.values(formValidationState).every(value => value === true);
                finalizeButton.disabled = !allValid;
                
                if (allValid) {
                    finalizeButton.classList.add('btn-success');
                    finalizeButton.classList.remove('btn-secondary');
                } else {
                    finalizeButton.classList.remove('btn-success');
                    finalizeButton.classList.add('btn-secondary');
                }
            }
        },
        
        // Função para validar manualmente o formulário
        validateFormManually: function() {
            return validateForm();
        },
        
        // Função para verificar o estado atual da validação
        getValidationState: function() {
            return {...formValidationState};
        }
    };
});
