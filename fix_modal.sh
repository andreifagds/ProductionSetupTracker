#!/bin/bash

# Adicionar código para fechar corretamente o modal
sed -i '/setupModalEventListeners/a\
\
    // Resolver problema da tela escura ao fechar modal\
    document.querySelectorAll("[data-bs-dismiss=modal]").forEach(button => {\
        button.addEventListener("click", function() {\
            // Remover backdrop manualmente quando o modal for fechado\
            setTimeout(() => {\
                document.querySelectorAll(".modal-backdrop").forEach(backdrop => {\
                    backdrop.remove();\
                });\
                document.body.classList.remove("modal-open");\
                document.body.style.overflow = "";\
                document.body.style.paddingRight = "";\
            }, 200);\
        });\
    });' static/js/audit-detail-modal.js

chmod +x fix_modal.sh
./fix_modal.sh

# Verificar se as alterações foram feitas
grep -n "Resolver problema da tela escura" static/js/audit-detail-modal.js
