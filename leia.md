# Para subir o servidor com um novo IP: 

1 - Digitar comando "sudo nano /etc/nginx/sites-available/flask_app"
2 - Alterar os "server_name" para o novo IP
3 - Digitar comando "systemctl restart nginx" para reiniciar o servidor

# Para verificar se o servidor está rodando

1 - Digitar comando "systemctl status nginx" e verificar se está em "Running"
2 - Digitar comando "systemctl status flask_app" e verificar se está em "Running"

# Resolver problema de erro ao cadastrar novos SETUPS

1 - Provavelmente a memória está muito cheia, vá em /home/inet/ProductionSetupTracker/dados_setup e exclua as pastas com os cadastros das OPs mais antigas

