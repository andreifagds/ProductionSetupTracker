// Implementação completa para o scanner QR baseada na abordagem da página de diagnóstico

// Função para adicionar logs
function scannerLog(message) {
    console.log(`[Scanner] ${message}`);
    const messageElement = document.getElementById('scannerMessage');
    if (messageElement) {
        messageElement.textContent = message;
    }
}

// Função para atualizar status
function updateScannerStatus(message, type) {
    scannerLog(message);
    
    // Atualizar o elemento de status dentro do scanner (interno)
    const statusDisplay = document.getElementById('scannerStatusDisplay');
    if (statusDisplay) {
        statusDisplay.innerHTML = `<span class="text-${type}">${message}</span>`;
    }
    
    // Esconder o elemento scanner-message (externo) para evitar duplicação
    const messageElement = document.getElementById('scannerMessage');
    if (messageElement) {
        messageElement.style.display = 'none';
    }
}

// Verificar suporte à câmera
async function checkCameraSupport() {
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            updateScannerStatus('Seu navegador não suporta a API de mídia necessária para acesso à câmera.', 'danger');
            return false;
        }
        
        // Tenta acessar a câmera para verificar se realmente funciona
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (stream) {
            // Libera o stream após o teste
            stream.getTracks().forEach(track => track.stop());
            return true;
        }
        return false;
    } catch (error) {
        console.error('Erro ao verificar suporte à câmera:', error);
        updateScannerStatus(`Erro ao acessar câmera: ${error.message}`, 'danger');
        return false;
    }
}

// Variáveis para controle do vídeo
let videoStream = null;
let videoElement = null;
let canvasElement = null;
let canvasContext = null;
let scanning = false;

// Parar scanner
function stopScanner() {
    scanning = false;
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    
    // Esconder elementos de vídeo
    if (videoElement) {
        videoElement.style.display = 'none';
    }
    
    // Mostrar botão de scan
    const scanBtnContainer = document.getElementById('scanBtnContainer');
    if (scanBtnContainer) {
        scanBtnContainer.style.display = 'block';
    }
    
    // Esconder container do scanner
    const scannerContainer = document.getElementById('scannerContainer');
    if (scannerContainer) {
        scannerContainer.style.display = 'none';
    }
    
    // Limpar e esconder o elemento de mensagem externa (evita duplicação)
    const scannerMessageElement = document.getElementById('scannerMessage');
    if (scannerMessageElement) {
        scannerMessageElement.innerHTML = '';
        scannerMessageElement.style.display = 'none';
    }
}

// Processar resultado do QR Code
function onQRCodeDetected(qrCode) {
    updateScannerStatus(`QR Code detectado: ${qrCode}`, 'success');
    
    // Dependendo da página, processar o QR code de forma apropriada
    const currentPath = window.location.pathname;
    
    if (currentPath.includes('/register_qrcode')) {
        // Estamos na página de registro de QR
        const qrCodeInput = document.getElementById('qrcodeValue');
        if (qrCodeInput) {
            qrCodeInput.value = qrCode;
        }
        
        // Também preencher automático o campo de célula
        const cellNameInput = document.getElementById('cellName');
        if (cellNameInput) {
            cellNameInput.value = qrCode;
        }
        
        // Mostrar mensagem de instrução
        updateScannerStatus(`QR Code capturado: ${qrCode}. Confirme o registro clicando em "Salvar QR Code".`, 'success');
        
        // Não parar scanner para mostrar a mensagem
        setTimeout(() => {
            stopScanner();
        }, 1500);
        
    } else if (currentPath.includes('/setup')) {
        // Estamos na página de setup, validar QR code
        fetch(`/api/get_cell_name/${encodeURIComponent(qrCode)}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // QR code válido
                    const cellNameInput = document.getElementById('cellName');
                    const cellNameHeader = document.getElementById('cellNameHeader');
                    const cellNameTypeSelection = document.getElementById('cellNameTypeSelection');
                    const setupTypeStatus = document.getElementById('setupTypeStatus');
                    const setupTypeRemovalBtn = document.getElementById('setupTypeRemoval');
                    const setupTypeSupplyBtn = document.getElementById('setupTypeSupply');
                    const orderNumberInput = document.getElementById('orderNumber');
                    
                    // Definir o nome da célula em todos os locais necessários
                    if (cellNameInput) {
                        cellNameInput.value = data.cell_name;
                    }
                    
                    if (cellNameHeader) {
                        cellNameHeader.textContent = data.cell_name;
                    }
                    
                    if (cellNameTypeSelection) {
                        cellNameTypeSelection.textContent = data.cell_name;
                    }
                    
                    // Definir o número da ordem de produção (se disponível)
                    if (orderNumberInput && data.most_recent_order) {
                        orderNumberInput.value = data.most_recent_order;
                    }
                    
                    // Processar o status dos setups
                    if (setupTypeStatus && data.setup_status) {
                        // Atualizar a mensagem de status para o usuário
                        setupTypeStatus.style.display = 'block';
                        
                        // Obter os elementos card para aplicar estilos
                        const removalCard = document.querySelector('.card[data-setup-type="removal"]') || 
                                            setupTypeRemovalBtn?.closest('.card');
                        const supplyCard = document.querySelector('.card[data-setup-type="supply"]') || 
                                          setupTypeSupplyBtn?.closest('.card');
                        
                        // Lista de registros existentes para exibição
                        let existingRecords = [];
                        if (data.setup_status.removal) existingRecords.push("Retirada");
                        if (data.setup_status.supply) existingRecords.push("Abastecimento");
                        
                        if (existingRecords.length > 0) {
                            // Mostrar mensagem informativa sobre registros existentes
                            setupTypeStatus.innerHTML = `
                                <strong>Status:</strong> Registros já realizados: ${existingRecords.join(' e ')}. 
                                <br>Você pode realizar qualquer operação a qualquer momento.
                            `;
                            setupTypeStatus.className = 'alert alert-info mb-4';
                            
                            // Atualizar estilo dos cards sem desabilitar nenhum
                            if (removalCard) {
                                removalCard.classList.remove('disabled');
                                if (data.setup_status.removal) {
                                    removalCard.classList.add('completed');
                                } else {
                                    removalCard.classList.remove('completed');
                                }
                            }
                            if (supplyCard) {
                                supplyCard.classList.remove('disabled');
                                if (data.setup_status.supply) {
                                    supplyCard.classList.add('completed');
                                } else {
                                    supplyCard.classList.remove('completed');
                                }
                            }
                        } else {
                            // Nenhum registro encontrado
                            setupTypeStatus.innerHTML = `
                                <strong>Status:</strong> Nenhum registro encontrado para esta célula. 
                                Escolha qualquer operação para iniciar.
                            `;
                            setupTypeStatus.className = 'alert alert-info mb-4';
                            
                            // Limpar estilos dos cards
                            if (removalCard) {
                                removalCard.classList.remove('disabled', 'completed', 'pending');
                            }
                            if (supplyCard) {
                                supplyCard.classList.remove('disabled', 'completed', 'pending');
                            }
                        }
                        
                        // Sempre habilitar ambos os botões, independentemente do status
                        if (setupTypeRemovalBtn) {
                            setupTypeRemovalBtn.disabled = false;
                            setupTypeRemovalBtn.classList.remove('disabled');
                        }
                        if (setupTypeSupplyBtn) {
                            setupTypeSupplyBtn.disabled = false;
                            setupTypeSupplyBtn.classList.remove('disabled');
                        }
                    }
                    
                    // Esconder o formulário de setup e mostrar a seleção de tipo
                    const setupFormContainer = document.getElementById('setupFormContainer');
                    const setupTypeSelectionContainer = document.getElementById('setupTypeSelectionContainer');
                    
                    if (setupFormContainer) {
                        setupFormContainer.style.display = 'none';
                    }
                    
                    if (setupTypeSelectionContainer) {
                        setupTypeSelectionContainer.style.display = 'block';
                    }
                    
                    // Mostrar display de célula
                    const cellNameDisplay = document.getElementById('cellNameDisplay');
                    if (cellNameDisplay) {
                        cellNameDisplay.style.display = 'block';
                    }
                    
                    updateScannerStatus(`Célula válida: ${data.cell_name}. Selecione o tipo de operação.`, 'success');
                    
                    // Não parar scanner para mostrar a mensagem
                    setTimeout(() => {
                        stopScanner();
                    }, 1500);
                } else {
                    // QR code inválido
                    updateScannerStatus('QR Code não cadastrado! É necessário cadastrar este QR Code antes de usá-lo.', 'danger');
                    
                    // Mostrar botões de opção no statusDisplay
                    const statusDisplay = document.getElementById('scannerStatusDisplay');
                    if (statusDisplay) {
                        const registerLink = document.createElement('div');
                        registerLink.className = 'mt-3';
                        registerLink.innerHTML = `
                            <p class="mb-2">Deseja cadastrar este QR Code?</p>
                            <a href="/register_qrcode" class="btn btn-success btn-sm">
                                <i class="fa fa-plus-circle me-1"></i> Ir para Cadastro de QR Code
                            </a>
                            <button class="btn btn-secondary btn-sm ms-2" onclick="stopScanner();">
                                <i class="fa fa-undo me-1"></i> Tentar Outro QR Code
                            </button>
                        `;
                        statusDisplay.appendChild(registerLink);
                    }
                }
            })
            .catch(error => {
                console.error('Erro ao validar QR code:', error);
                updateScannerStatus('Erro ao validar QR Code. Tente novamente.', 'danger');
                
                // Mostrar botão de tentativa novamente
                const statusDisplay = document.getElementById('scannerStatusDisplay');
                if (statusDisplay) {
                    const retryButton = document.createElement('div');
                    retryButton.className = 'mt-3 text-center';
                    retryButton.innerHTML = `
                        <button class="btn btn-warning btn-sm" onclick="stopScanner();">
                            <i class="fa fa-refresh me-1"></i> Tentar Novamente
                        </button>
                    `;
                    statusDisplay.appendChild(retryButton);
                }
            });
    } else {
        // Estamos em outra página, simplesmente parar o scanner
        stopScanner();
    }
}

// Iniciar scanner
async function startQRScanner() {
    const cameraSupported = await checkCameraSupport();
    
    if (!cameraSupported) {
        updateScannerStatus('Câmera não disponível. Verifique as permissões do navegador.', 'danger');
        return;
    }
    
    // Esconder botão de scan e mostrar scanner
    const scanBtnContainer = document.getElementById('scanBtnContainer');
    const scannerContainer = document.getElementById('scannerContainer');
    
    if (scanBtnContainer) {
        scanBtnContainer.style.display = 'none';
    }
    
    if (scannerContainer) {
        scannerContainer.style.display = 'block';
    }
    
    // Criar status display se não existir
    let statusDisplay = document.getElementById('scannerStatusDisplay');
    if (!statusDisplay) {
        statusDisplay = document.createElement('div');
        statusDisplay.id = 'scannerStatusDisplay';
        statusDisplay.className = 'scanner-message mt-3';
        scannerContainer.appendChild(statusDisplay);
    }
    
    // Inicializar elementos de vídeo
    videoElement = document.createElement('video');
    videoElement.id = 'qr-video';
    videoElement.style.width = '100%';
    videoElement.style.maxWidth = '400px';
    videoElement.style.margin = '0 auto';
    videoElement.style.border = '1px solid #666';
    videoElement.style.borderRadius = '4px';
    
    // Criar contêiner para vídeo se não existir
    let videoContainer = document.getElementById('reader');
    if (!videoContainer) {
        videoContainer = document.createElement('div');
        videoContainer.id = 'reader';
        scannerContainer.prepend(videoContainer);
    }
    
    // Limpar contêiner de vídeo e adicionar o elemento de vídeo
    videoContainer.innerHTML = '';
    videoContainer.appendChild(videoElement);
    
    // Adicionar instruções
    const instructions = document.createElement('div');
    instructions.className = 'text-center mt-2 mb-3';
    instructions.innerHTML = `
        <small class="text-muted">Posicione o QR Code no centro da câmera para escaneá-lo automaticamente.</small>
    `;
    videoContainer.appendChild(instructions);
    
    // Criar elementos de canvas para processamento
    canvasElement = document.createElement('canvas');
    canvasElement.style.display = 'none';
    videoContainer.appendChild(canvasElement);
    canvasContext = canvasElement.getContext('2d');
    
    updateScannerStatus('Iniciando câmera...', 'info');
    
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment" }
        });
        
        if (!videoStream) {
            throw new Error('Falha ao inicializar stream de vídeo');
        }
        
        videoElement.srcObject = videoStream;
        videoElement.setAttribute('playsinline', true); // Necessário para iOS
        videoElement.play();
        
        scanning = true;
        updateScannerStatus('Câmera ativa. Aponte para um QR Code.', 'success');
        
        // Adicionar botão para cancelar
        const cancelButton = document.createElement('button');
        cancelButton.className = 'btn btn-outline-secondary btn-sm mt-3';
        cancelButton.innerHTML = '<i class="fa fa-times me-1"></i> Cancelar';
        cancelButton.onclick = stopScanner;
        videoContainer.appendChild(cancelButton);
        
        // Iniciar o loop de escaneamento
        requestAnimationFrame(scan);
        
    } catch (error) {
        console.error('Erro ao iniciar scanner:', error);
        updateScannerStatus(`Erro ao iniciar câmera: ${error.message}`, 'danger');
    }
    
    // Função de escaneamento
    function scan() {
        if (!scanning) {
            return;
        }
        
        if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
            // Ajustar canvas para o tamanho do vídeo
            canvasElement.height = videoElement.videoHeight;
            canvasElement.width = videoElement.videoWidth;
            
            // Desenhar frame do vídeo no canvas
            canvasContext.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
            
            // Obter dados da imagem
            const imageData = canvasContext.getImageData(0, 0, canvasElement.width, canvasElement.height);
            
            // Escanear QR code usando jsQR
            const code = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "dontInvert",
            });
            
            if (code) {
                // QR code detectado
                console.log('QR code detectado:', code.data);
                
                // Desenhar linhas de marcação
                drawQRHighlight(code.location, 'green');
                
                // Processar o resultado e pausar o escaneamento
                scanning = false;
                onQRCodeDetected(code.data);
                
                // Não continuar o loop de escaneamento
                return;
            }
        }
        
        // Continuar o loop de escaneamento
        requestAnimationFrame(scan);
    }
    
    // Função para desenhar destaque no QR code
    function drawQRHighlight(location, color) {
        canvasContext.beginPath();
        canvasContext.moveTo(location.topLeftCorner.x, location.topLeftCorner.y);
        canvasContext.lineTo(location.topRightCorner.x, location.topRightCorner.y);
        canvasContext.lineTo(location.bottomRightCorner.x, location.bottomRightCorner.y);
        canvasContext.lineTo(location.bottomLeftCorner.x, location.bottomLeftCorner.y);
        canvasContext.lineTo(location.topLeftCorner.x, location.topLeftCorner.y);
        canvasContext.lineWidth = 4;
        canvasContext.strokeStyle = color;
        canvasContext.stroke();
    }
}

// Escutar clique no botão de scan
function scanQRCode() {
    // Obter elementos da UI
    const scanQrCodeBtn = document.getElementById('scanQrCodeBtn');
    const scannerContainer = document.getElementById('scannerContainer');
    
    // Verificar se os elementos existem
    if (scanQrCodeBtn && scannerContainer) {
        scanQrCodeBtn.addEventListener('click', startQRScanner);
    }
}

// Função para configurar o formulário com base no tipo de setup (retirada ou abastecimento)
function setupFormForType(setupType) {
    const setupTypeInput = document.getElementById('setupType');
    const setupTypeTitle = document.getElementById('setupTypeTitle');
    const operatorLabel = document.getElementById('operatorLabel');
    const verificationLabel = document.getElementById('verificationLabel');

    console.log("[SETUP-FORM] Configurando formulário para o tipo:", setupType);

    if (setupTypeInput) {
        setupTypeInput.value = setupType;
    }

    if (setupType === 'removal') {
        // Configurar para remoção
        if (setupTypeTitle) setupTypeTitle.textContent = 'Retirada de Material';
        if (operatorLabel) operatorLabel.textContent = 'Operador da Retirada';
        if (verificationLabel) {
            verificationLabel.textContent = 'Confirmo que realizei a retirada completa dos materiais do produto anterior';
        }
        
        // Remover validação de campos de produto para retirada
        const productCodeInput = document.getElementById('productCode');
        const productSelectionInput = document.getElementById('productSelection');
        
        if (productCodeInput) {
            productCodeInput.removeAttribute('required');
            console.log("[SETUP-FORM] Removendo atributo required do produtCode para modo retirada");
        }
        
        if (productSelectionInput) {
            productSelectionInput.removeAttribute('required');
            console.log("[SETUP-FORM] Removendo atributo required do productSelection para modo retirada");
        }
        
    } else {
        // Configurar para abastecimento
        if (setupTypeTitle) setupTypeTitle.textContent = 'Abastecimento de Material';
        if (operatorLabel) operatorLabel.textContent = 'Abastecedor';
        if (verificationLabel) {
            verificationLabel.textContent = 'Confirmo que realizei o abastecimento correto de todos os materiais para o novo produto';
        }
        
        // Adicionar validação para campos de produto em abastecimento
        const productCodeInput = document.getElementById('productCode');
        const productSelectionInput = document.getElementById('productSelection');
        
        if (productCodeInput) {
            productCodeInput.setAttribute('required', 'required');
            console.log("[SETUP-FORM] Adicionando atributo required ao produtCode para modo abastecimento");
        }
        
        if (productSelectionInput) {
            productSelectionInput.setAttribute('required', 'required');
            console.log("[SETUP-FORM] Adicionando atributo required ao productSelection para modo abastecimento");
        }
    }

    // Mostrar ou esconder campos de produto e itens baseado no tipo de setup
    const supplyFields = document.querySelectorAll('.supply-fields');
    
    if (setupType === 'removal') {
        // Esconder campos de produto para retirada
        supplyFields.forEach(field => field.style.display = 'none');
    } else {
        // Mostrar campos de produto para abastecimento
        supplyFields.forEach(field => field.style.display = 'block');
        
        // Verificar se há produtos disponíveis
        const productSelection = document.getElementById('productSelection');
        if (productSelection) {
            // Limpar possíveis alertas anteriores
            const existingAlert = document.querySelector('.product-alert-message');
            if (existingAlert) {
                existingAlert.remove();
            }
            
            // Verificar se há produtos cadastrados para esta célula
            if (productSelection.options.length <= 1) {
                console.log('Nenhum produto encontrado para esta célula:', productSelection.options.length);
                
                // Exibir uma mensagem de alerta
                const alertMessage = document.createElement('div');
                alertMessage.className = 'alert alert-warning mt-3 product-alert-message';
                alertMessage.innerHTML = `
                    <i class="fa fa-exclamation-triangle me-2"></i>
                    <strong>Atenção:</strong> Nenhum produto cadastrado para esta célula.
                    Por favor, solicite a um auditor para cadastrar produtos na célula.
                `;
                
                // Inserir o alerta antes do primeiro campo de produto
                if (supplyFields.length > 0) {
                    supplyFields[0].before(alertMessage);
                }
            }
        }
    }
    
    // Forçar execução de validação após mudar o tipo
    if (window.validateForm) {
        console.log("[SETUP-FORM] Executando validação do formulário após mudar tipo");
        setTimeout(window.validateForm, 100);
    }
}

// Inicialização do scanner quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar listener ao botão de scan
    scanQRCode();
    
    // Obter elementos de setup para setup.html
    const setupTypeButtons = document.querySelectorAll('.btn-setup-type');
    const setupForm = document.getElementById('setupForm');
    
    // Setup para os botões de tipo de setup
    if (setupTypeButtons.length > 0) {
        setupTypeButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Obter o tipo de setup do botão
                const setupType = this.getAttribute('data-setup-type');
                if (!setupType) return;
                
                // Configurar o formulário para o tipo
                setupFormForType(setupType);
                
                // Esconder seleção de tipo e mostrar formulário
                const setupTypeSelectionContainer = document.getElementById('setupTypeSelectionContainer');
                const setupFormContainer = document.getElementById('setupFormContainer');
                
                if (setupTypeSelectionContainer) setupTypeSelectionContainer.style.display = 'none';
                if (setupFormContainer) setupFormContainer.style.display = 'block';
            });
        });
    }
    
    // Botão de reset de célula
    const resetCellFlowBtn = document.getElementById('resetCellFlowBtn');
    if (resetCellFlowBtn) {
        resetCellFlowBtn.addEventListener('click', function() {
            const cellName = document.getElementById('cellNameTypeSelection')?.textContent;
            if (!cellName) return;
            
            // Solicitar motivo do reset
            const reason = prompt('Por favor, informe o motivo para resetar o fluxo desta célula:');
            if (!reason) return; // Usuário cancelou
            
            // Enviar requisição para o backend
            fetch('/api/reset_cell', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cell_name: cellName,
                    reason: reason
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Fluxo da célula resetado com sucesso. Agora todas as operações estão disponíveis.');
                    // Recarregar a página para atualizar o status
                    window.location.reload();
                } else {
                    alert('Erro ao resetar fluxo: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Erro ao resetar célula:', error);
                alert('Erro ao comunicar com o servidor. Tente novamente.');
            });
        });
    }
});
