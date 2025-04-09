
    // Mostrar ou esconder campos de produto e itens baseado no tipo de setup
    const supplyFields = document.querySelectorAll('.supply-fields');
    
    if (setupType === 'removal') {
        // Esconder campos de produto para retirada
        supplyFields.forEach(field => field.style.display = 'none');
    } else {
        // Mostrar campos de produto para abastecimento
        supplyFields.forEach(field => field.style.display = 'block');
    }
