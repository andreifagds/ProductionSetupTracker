// Main JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });

    // Reset Cell Flow Button Functionality
    const resetCellFlowBtn = document.getElementById('resetCellFlowBtn');
    if (resetCellFlowBtn) {
        resetCellFlowBtn.addEventListener('click', function() {
            // Get cell name from the header or hidden field
            const cellName = document.getElementById('cellNameHeader').textContent || 
                           document.getElementById('cellNameTypeSelection').textContent;
            
            // Update modal with cell name
            document.getElementById('resetCellName').textContent = cellName;
            
            // Show the reset modal
            const resetCellModal = new bootstrap.Modal(document.getElementById('resetCellModal'));
            resetCellModal.show();
        });
        
        // Handle reset confirmation
        const confirmResetBtn = document.getElementById('confirmResetBtn');
        if (confirmResetBtn) {
            confirmResetBtn.addEventListener('click', function() {
                const resetReason = document.getElementById('resetReason');
                const cellName = document.getElementById('resetCellName').textContent;
                
                // Verificar se o motivo foi preenchido
                if (!resetReason.value.trim()) {
                    resetReason.classList.add('is-invalid');
                    return;
                }
                
                resetReason.classList.remove('is-invalid');
                
                // Mostrar indicador de carregamento
                const originalBtnText = confirmResetBtn.innerHTML;
                confirmResetBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';
                confirmResetBtn.disabled = true;
                
                // Enviar requisição à API
                fetch('/api/reset_cell', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        cell_name: cellName,
                        reset_reason: resetReason.value
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Fechar modal
                        bootstrap.Modal.getInstance(document.getElementById('resetCellModal')).hide();
                        
                        // Exibir mensagem de sucesso
                        alert(data.message);
                        
                        // Atualizar a página para refletir o novo estado
                        location.reload();
                    } else {
                        throw new Error(data.message || 'Erro ao resetar fluxo da célula');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    
                    // Exibir mensagem de erro
                    alert('Erro: ' + (error.message || 'Falha ao resetar fluxo da célula'));
                })
                .finally(() => {
                    // Restaurar botão
                    confirmResetBtn.innerHTML = originalBtnText;
                    confirmResetBtn.disabled = false;
                });
            });
        }
    }

    // Setup form validation
    const setupForm = document.getElementById('setupForm');
    if (setupForm) {
        setupForm.addEventListener('submit', function(event) {
            if (!setupForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            setupForm.classList.add('was-validated');
        });

        // Handle photo upload
        const photoInput = document.getElementById('photoInput');
        const photoDataInput = document.getElementById('photoData');
        
        if (photoInput && photoDataInput) {
            // Array para armazenar as imagens comprimidas
            let compressedImages = [];
            
            photoInput.addEventListener('change', function(event) {
                const files = event.target.files;
                if (files.length === 0) return;
                
                // Limpar arrays e exibições anteriores
                compressedImages = [];
                const carouselInner = document.getElementById('carouselInner');
                carouselInner.innerHTML = '';
                
                // Contador para controlar quando todas as imagens foram processadas
                let processedCount = 0;
                
                // Para cada arquivo selecionado
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    const reader = new FileReader();
                    
                    reader.onload = function(e) {
                        // Criar uma imagem para manipulação
                        const img = new Image();
                        img.onload = function() {
                            // Criar um canvas para redimensionar/comprimir
                            const canvas = document.createElement('canvas');
                            
                            // Calcular novas dimensões mantendo proporção
                            let width = img.width;
                            let height = img.height;
                            const maxDimension = 1200;
                            
                            if (width > maxDimension || height > maxDimension) {
                                if (width > height) {
                                    height = Math.round(height * (maxDimension / width));
                                    width = maxDimension;
                                } else {
                                    width = Math.round(width * (maxDimension / height));
                                    height = maxDimension;
                                }
                            }
                            
                            // Redimensionar no canvas
                            canvas.width = width;
                            canvas.height = height;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0, width, height);
                            
                            // Converter para JPEG com qualidade reduzida (0.2 = 20%)
                            const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.2);
                            
                            // Adicionar ao array de imagens comprimidas
                            compressedImages.push(compressedDataUrl);
                            
                            // Criar item do carrossel
                            const carouselItem = document.createElement('div');
                            carouselItem.className = 'carousel-item' + (processedCount === 0 ? ' active' : '');
                            
                            const imgContainer = document.createElement('div');
                            imgContainer.className = 'd-flex justify-content-center';
                            
                            const imgElement = document.createElement('img');
                            imgElement.src = compressedDataUrl;
                            imgElement.className = 'img-fluid';
                            imgElement.alt = `Imagem ${processedCount + 1}`;
                            
                            imgContainer.appendChild(imgElement);
                            carouselItem.appendChild(imgContainer);
                            carouselInner.appendChild(carouselItem);
                            
                            processedCount++;
                            
                            // Atualizar o contador de imagens
                            const imageCounter = document.getElementById('imageCounter');
                            imageCounter.classList.remove('d-none');
                            const badge = imageCounter.querySelector('.badge');
                            badge.textContent = `${processedCount} ${processedCount === 1 ? 'imagem selecionada' : 'imagens selecionadas'}`;
                            
                            // Quando todas as imagens forem processadas
                            if (processedCount === files.length) {
                                // Remover o placeholder se existir
                                const placeholder = document.getElementById('noImagePlaceholder');
                                if (placeholder && placeholder.parentNode) {
                                    const placeholderItem = placeholder.closest('.carousel-item');
                                    if (placeholderItem) {
                                        placeholderItem.remove();
                                    }
                                }
                                
                                // Adicionar controles do carrossel se houver mais de uma imagem
                                const carousel = document.getElementById('imagesCarousel');
                                
                                if (processedCount > 1 && !carousel.querySelector('.carousel-control-prev')) {
                                    // Adicionar botões de navegação
                                    const prevButton = document.createElement('button');
                                    prevButton.className = 'carousel-control-prev';
                                    prevButton.type = 'button';
                                    prevButton.setAttribute('data-bs-target', '#imagesCarousel');
                                    prevButton.setAttribute('data-bs-slide', 'prev');
                                    prevButton.innerHTML = `
                                        <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                                        <span class="visually-hidden">Anterior</span>
                                    `;
                                    
                                    const nextButton = document.createElement('button');
                                    nextButton.className = 'carousel-control-next';
                                    nextButton.type = 'button';
                                    nextButton.setAttribute('data-bs-target', '#imagesCarousel');
                                    nextButton.setAttribute('data-bs-slide', 'next');
                                    nextButton.innerHTML = `
                                        <span class="carousel-control-next-icon" aria-hidden="true"></span>
                                        <span class="visually-hidden">Próximo</span>
                                    `;
                                    
                                    carousel.appendChild(prevButton);
                                    carousel.appendChild(nextButton);
                                }
                                
                                // Concatenar todas as imagens comprimidas em uma string JSON e armazenar no campo oculto
                                photoDataInput.value = JSON.stringify(compressedImages);
                            }
                        };
                        img.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                }
            });
        }

        // Check if we need to enable/disable the submit button
        const verificationCheckbox = document.getElementById('verificationCheck');
        const finalizeButton = document.getElementById('finalizeButton');
        
        if (verificationCheckbox && finalizeButton) {
            function updateButtonState() {
                const orderNumberValid = document.getElementById('orderNumber').value.trim() !== '';
                
                // Verificar o perfil do usuário (se é supplier ou não)
                const userProfile = document.getElementById('supplierUserContainer');
                const supplierInputContainer = document.getElementById('supplierInputContainer');
                
                // Para abastecedores, não precisamos verificar o campo supplierName
                let supplierNameValid = true;
                
                // Se o campo de entrada manual estiver visível, verificamos se está preenchido
                if (supplierInputContainer && supplierInputContainer.style.display !== 'none') {
                    const supplierNameInput = document.getElementById('supplierName');
                    if (supplierNameInput) {
                        supplierNameValid = supplierNameInput.value.trim() !== '';
                    }
                }
                
                // Verificar se temos pelo menos uma imagem
                const photoValid = photoDataInput.value !== '';
                const checkboxValid = verificationCheckbox.checked;
                
                finalizeButton.disabled = !(orderNumberValid && supplierNameValid && photoValid && checkboxValid);
            }
            
            verificationCheckbox.addEventListener('change', updateButtonState);
            document.getElementById('orderNumber').addEventListener('input', updateButtonState);
            document.getElementById('supplierName').addEventListener('input', updateButtonState);
            photoInput.addEventListener('change', updateButtonState);
            
            // Initial check
            updateButtonState();
        }
    }

    // Handle QR code scanner activation
    const scanQrCodeBtn = document.getElementById('scanQrCodeBtn');
    if (scanQrCodeBtn) {
        scanQrCodeBtn.addEventListener('click', function() {
            // Start QR code scanner using camera-scanner.js
            startQRScanner();
        });
    }

    // Handle audit editing
    const editSetupBtns = document.querySelectorAll('.edit-setup-btn');
    if (editSetupBtns.length > 0) {
        editSetupBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const setupId = this.getAttribute('data-setup-id');
                const cellName = this.getAttribute('data-cell-name');
                const orderNumber = this.getAttribute('data-order-number');
                const supplierName = this.getAttribute('data-supplier-name');
                const observation = this.getAttribute('data-observation');
                const verificationCheck = this.getAttribute('data-verification-check') === 'True';
                
                // Fill in the edit modal with the setup data
                const modal = document.getElementById('editSetupModal');
                if (modal) {
                    modal.querySelector('#editCellName').value = cellName;
                    modal.querySelector('#editOrderNumber').value = orderNumber;
                    modal.querySelector('#editSupplierName').value = supplierName;
                    modal.querySelector('#editObservation').value = observation;
                    modal.querySelector('#editVerificationCheck').checked = verificationCheck;
                    
                    // Set up the save button
                    const saveBtn = modal.querySelector('#saveSetupBtn');
                    saveBtn.addEventListener('click', function() {
                        updateSetup(cellName, orderNumber);
                    });
                    
                    // Show the modal
                    const modalInstance = new bootstrap.Modal(modal);
                    modalInstance.show();
                }
            });
        });
    }
});

// Function to update a setup via API
function updateSetup(cellName, orderNumber, supplierName, observation, verificationCheck, audited, auditorName, setupType, photoData, timestamp) {
    let modal;
    let saveBtn;
    let originalBtnText;
    
    // Se os parâmetros não foram fornecidos, obtê-los do modal
    if (arguments.length < 3) {
        modal = document.getElementById('editSetupModal');
        supplierName = modal.querySelector('#editSupplierName').value;
        observation = modal.querySelector('#editObservation').value;
        verificationCheck = modal.querySelector('#editVerificationCheck').checked;
        setupType = modal.querySelector('#editSetupType')?.value;
        photoData = modal.querySelector('#editPhotoData')?.value;
        timestamp = modal.querySelector('#editTimestamp')?.value;
        
        // Obter referência ao botão de salvar dentro do modal
        saveBtn = modal.querySelector('#saveSetupBtn');
        originalBtnText = saveBtn.innerHTML;
        
        // Mostrar indicador de loading
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
        saveBtn.disabled = true;
    }
    
    // Create data object
    const data = {
        cell_name: cellName,
        order_number: orderNumber,
        supplier_name: supplierName,
        observation: observation,
        verification_check: verificationCheck
    };
    
    // Adicionar parâmetros opcionais se fornecidos
    if (audited !== undefined) data.audited = audited;
    if (auditorName) data.auditor_name = auditorName;
    if (setupType) data.setup_type = setupType;
    if (photoData) data.photo_data = photoData;
    if (timestamp) data.timestamp = timestamp;
    
    // Send API request
    fetch('/api/update_setup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(responseData => {
        if (responseData.success) {
            // Close modal se estiver definido
            if (modal) {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) modalInstance.hide();
            }
            
            // Show success message
            const alertContainer = document.getElementById('alertContainer');
            if (alertContainer) {
                alertContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        Setup atualizado com sucesso!
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
                
                // Refresh the page after a short delay
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                // No caso de chamada direta (sem UI), apenas recarregar a página
                location.reload();
            }
        } else {
            throw new Error(responseData.message || 'Erro ao atualizar setup');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Show error message if UI exists
        const alertContainer = document.getElementById('alertContainer');
        if (alertContainer) {
            alertContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    ${error.message || 'Erro ao atualizar setup'}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
    })
    .finally(() => {
        // Restore button if it exists
        if (saveBtn) {
            saveBtn.innerHTML = originalBtnText;
            saveBtn.disabled = false;
        }
    });
}
