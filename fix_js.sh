#!/bin/bash

# Criar backup do arquivo original
cp static/js/audit-detail-modal.js static/js/audit-detail-modal.js.bak

# Substituir a parte do código que faz o parse do JSON
sed -i 's/    try {
        \/\/ Tentar converter setupDetails para objeto se for string
        const setupDetailsObj = typeof setupDetails === '\''string'\'' ? JSON.parse(setupDetails) : setupDetails;/    try {
        \/\/ Tentar converter setupDetails para objeto se for string
        let setupDetailsObj;
        
        if (typeof setupDetails === '\''string'\'') {
            try {
                setupDetailsObj = JSON.parse(setupDetails);
            } catch (parseError) {
                console.error("Erro ao fazer parse do JSON:", parseError, "Dados recebidos:", setupDetails);
                alert("Erro ao processar dados. Por favor, tente novamente ou contate o suporte.");
                return;
            }
        } else {
            setupDetailsObj = setupDetails;
        }/' static/js/audit-detail-modal.js

echo "Arquivo JS modificado!"
