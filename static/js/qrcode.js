// QR Code scanner functionality using HTML5-QRCode library

let html5QrCode;

// Função para verificar se o navegador suporta acesso à câmera
function checkCameraSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Seu navegador não suporta acesso à câmera');
        return false;
    }
    return true;
}

// Função para solicitar permissão de câmera
async function requestCameraPermission() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        // Parar o stream após obter a permissão
        stream.getTracks().forEach(track => track.stop());
        return true;
    } catch (error) {
        console.error('Erro ao solicitar permissão de câmera:', error);
        return false;
    }
}

// Initialize QR Code Scanner
async function initializeQrScanner() {
    const scannerContainer = document.getElementById('reader');
    const scannerMessageContainer = document.getElementById('scannerMessage');
    
    // Show scanner container
    document.getElementById('scannerContainer').style.display = 'block';
    
    // Hide any previous messages
    if (scannerMessageContainer) {
        scannerMessageContainer.textContent = 'Iniciando câmera...';
    }
    
    // Verificar suporte à câmera
    if (!checkCameraSupport()) {
        if (scannerMessageContainer) {
            scannerMessageContainer.textContent = 'Seu navegador não suporta acesso à câmera.';
            scannerMessageContainer.classList.add('text-danger');
        }
        return;
    }
    
    // Solicitar permissão de câmera
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) {
        if (scannerMessageContainer) {
            scannerMessageContainer.textContent = 'Permissão de câmera negada. Por favor, permita o acesso à câmera e tente novamente.';
            scannerMessageContainer.classList.add('text-danger');
        }
        return;
    }
    
    // Initialize scanner if not already done
    if (!html5QrCode) {
        try {
            html5QrCode = new Html5Qrcode("reader");
            console.log('QR scanner initialized successfully');
        } catch (error) {
            console.error('Error initializing QR scanner:', error);
            if (scannerMessageContainer) {
                scannerMessageContainer.textContent = 'Erro ao inicializar o scanner. Tente recarregar a página.';
                scannerMessageContainer.classList.add('text-danger');
            }
            return;
        }
    }
    
    const qrCodeSuccessCallback = (decodedText) => {
        // Stop scanning
        html5QrCode.stop().then(() => {
            console.log('QR Code scanning stopped.');
            processQrCode(decodedText);
        }).catch((err) => {
            console.error('Error stopping QR Code scanner:', err);
        });
    };
    
    const config = { fps: 10, qrbox: { width: 250, height: 250 } };
    
    html5QrCode.start(
        { facingMode: "environment" }, // Use rear camera
        config,
        qrCodeSuccessCallback,
        (errorMessage) => {
            // Error callback (optional)
            console.log(errorMessage);
        }
    ).catch((err) => {
        console.error('Error starting QR Code scanner:', err);
        if (scannerMessageContainer) {
            scannerMessageContainer.textContent = 'Erro ao iniciar o scanner. Verifique se permitiu o acesso à câmera.';
            scannerMessageContainer.classList.add('text-danger');
        }
    });
}

function processQrCode(qrCodeValue) {
    console.log('QR Code detected:', qrCodeValue);
    
    const scannerMessageContainer = document.getElementById('scannerMessage');
    if (scannerMessageContainer) {
        scannerMessageContainer.textContent = 'QR Code detectado! Verificando...';
        scannerMessageContainer.classList.remove('text-danger');
        scannerMessageContainer.classList.add('text-success');
    }
    
    // Hide scanner container
    document.getElementById('scannerContainer').style.display = 'none';
    
    // Check page context
    const currentPath = window.location.pathname;
    
    if (currentPath.includes('/setup')) {
        // We're on the setup page, validate QR code
        validateQrCodeForSetup(qrCodeValue);
    } else if (currentPath.includes('/register_qrcode')) {
        // We're on the register QR code page
        document.getElementById('qrcodeValue').value = qrCodeValue;
        scannerMessageContainer.textContent = 'QR Code capturado! Agora insira o nome da célula.';
    } else {
        // We're on the main page or somewhere else, redirect to setup with the QR code
        window.location.href = `/setup?qrcode=${encodeURIComponent(qrCodeValue)}`;
    }
}

function validateQrCodeForSetup(qrCodeValue) {
    // Check if the QR code is registered
    fetch(`/api/get_cell_name/${encodeURIComponent(qrCodeValue)}`)
        .then(response => response.json())
        .then(data => {
            const scannerMessageContainer = document.getElementById('scannerMessage');
            
            if (data.success) {
                // QR code is valid, set the cell name in the form
                document.getElementById('cellName').value = data.cell_name;
                document.getElementById('cellNameHeader').textContent = data.cell_name;
                document.getElementById('cellNameDisplay').style.display = 'block';
                
                if (scannerMessageContainer) {
                    scannerMessageContainer.textContent = `QR Code válido: Célula "${data.cell_name}"`;
                    scannerMessageContainer.classList.add('text-success');
                }
                
                // Show setup form
                document.getElementById('setupFormContainer').style.display = 'block';
            } else {
                // QR code is not registered
                if (scannerMessageContainer) {
                    scannerMessageContainer.textContent = 'QR Code não encontrado no sistema. Por favor, registre-o primeiro.';
                    scannerMessageContainer.classList.add('text-danger');
                }
                
                // Show scan button again
                document.getElementById('scanBtnContainer').style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error validating QR code:', error);
            const scannerMessageContainer = document.getElementById('scannerMessage');
            
            if (scannerMessageContainer) {
                scannerMessageContainer.textContent = 'Erro ao validar QR Code. Tente novamente.';
                scannerMessageContainer.classList.add('text-danger');
            }
            
            // Show scan button again
            document.getElementById('scanBtnContainer').style.display = 'block';
        });
}
