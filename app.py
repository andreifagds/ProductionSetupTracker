import os
import json
import logging
import datetime
import base64
import shutil
from io import BytesIO
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, 
    url_for, session, flash, jsonify, send_from_directory
)


# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "setup_tracking_secret_key")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.debug = True


# Ensure necessary directories exist
def ensure_dir(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)

# Root data directory
DATA_DIR = "dados_setup"
ensure_dir(DATA_DIR)

# Initialize users.json and qrcodes.json if they don't exist
def init_data_files():
    """Initialize data files if they don't exist."""
    users_file = os.path.join(DATA_DIR, "users.json")
    qrcodes_file = os.path.join(DATA_DIR, "qrcodes.json")
    
    # Create users.json with a default admin user if it doesn't exist
    if not os.path.exists(users_file):
        with open(users_file, 'w') as f:
            # Alterado para hash mais simples para fins de demonstração
            json.dump([{
                "username": "admin",
                "password": generate_password_hash("admin123")
            }], f)
    else:
        # Tentar reconstruir o arquivo users.json para garantir que a senha funcione
        try:
            logging.debug("Tentando recriar o usuário admin")
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            # Atualizar a senha do admin, se existir
            for user in users:
                if user['username'] == 'admin':
                    user['password'] = generate_password_hash("admin123")
                    logging.debug("Senha do admin atualizada")
                    break
            
            # Se não houver admin, criar um
            if not any(user['username'] == 'admin' for user in users):
                users.append({
                    "username": "admin",
                    "password": generate_password_hash("admin123")
                })
                logging.debug("Novo usuário admin criado")
            
            # Salvar arquivo atualizado
            with open(users_file, 'w') as f:
                json.dump(users, f)
        except Exception as e:
            logging.error(f"Erro ao atualizar users.json: {e}")
    
    # Create qrcodes.json if it doesn't exist
    if not os.path.exists(qrcodes_file):
        with open(qrcodes_file, 'w') as f:
            json.dump({}, f)

init_data_files()

# Nota: A atualização do formato dos QR codes será chamada após todas as funções estarem definidas

def get_users():
    """Get all users from users.json."""
    try:
        with open(os.path.join(DATA_DIR, "users.json"), 'r') as f:
            users_list = json.load(f)
            # Converter lista para dicionário para facilitar a manipulação
            users_dict = {}
            for user in users_list:
                username = user.get('username')
                if username:
                    users_dict[username] = {
                        'password': user.get('password'),
                        'last_updated': user.get('last_updated', ''),
                        'profile': user.get('profile', 'auditor')  # Por padrão, usuários existentes serão auditores
                    }
            return users_dict
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading users: {e}")
        return {}
        
def save_users(users_dict):
    """Save users dictionary to users.json in list format."""
    users_list = []
    for username, data in users_dict.items():
        user_entry = {
            'username': username,
            'password': data.get('password'),
            'profile': data.get('profile', 'auditor')
        }
        if 'last_updated' in data:
            user_entry['last_updated'] = data['last_updated']
        users_list.append(user_entry)
    
    with open(os.path.join(DATA_DIR, "users.json"), 'w') as f:
        json.dump(users_list, f)
        
def add_user(username, password, profile='auditor'):
    """Add a new user or update existing user.
    
    Args:
        username: Nome do usuário
        password: Senha do usuário
        profile: Perfil do usuário ('auditor' ou 'supplier')
    """
    users = get_users()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Garantir que o perfil seja válido
    if profile not in ['auditor', 'supplier']:
        profile = 'auditor'
    
    # Garantir que o primeiro usuário 'admin' seja sempre auditor
    if username == 'admin':
        profile = 'auditor'
    
    # Adicionar novo usuário ou atualizar existente
    users[username] = {
        'password': generate_password_hash(password),
        'last_updated': timestamp,
        'profile': profile
    }
    
    save_users(users)
    return True
    
def delete_user(username):
    """Delete a user."""
    users = get_users()
    if username in users:
        # Não permitir excluir o último usuário
        if len(users) <= 1:
            return False
        
        # Não permitir excluir o usuário 'admin'
        if username == 'admin':
            return False
            
        del users[username]
        save_users(users)
        return True
    return False
    
def authenticate_user(username, password):
    """Authenticate a user with username and password."""
    users = get_users()
    if username in users:
        stored_hash = users[username]['password']
        return check_password_hash(stored_hash, password)
    return False

def get_qrcodes():
    """Get all QR codes from qrcodes.json."""
    try:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading QR codes: {e}")
        return {}

def save_qrcode(qrcode_value, cell_name):
    """Save a new QR code and cell name mapping."""
    qrcodes = get_qrcodes()
    
    # Usar o novo formato com estrutura para produtos
    qrcodes[qrcode_value] = {
        "cell_name": cell_name,
        "products": []
    }
    
    with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
        json.dump(qrcodes, f)
        
def update_qrcode(qrcode_value, new_cell_name):
    """Atualizar um QR code existente.
    
    Args:
        qrcode_value: Valor do QR code 
        new_cell_name: Novo nome da célula
        
    Returns:
        bool: True se atualizado com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    
    if qrcode_value in qrcodes:
        if isinstance(qrcodes[qrcode_value], dict):
            qrcodes[qrcode_value]["cell_name"] = new_cell_name
        else:
            # Converter formato antigo para novo
            qrcodes[qrcode_value] = {
                "cell_name": new_cell_name,
                "products": []
            }
        
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
    
    return False
    
def delete_qrcode(qrcode_value):
    """Excluir um QR code.
    
    Args:
        qrcode_value: Valor do QR code a ser excluído
        
    Returns:
        bool: True se excluído com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    
    if qrcode_value in qrcodes:
        del qrcodes[qrcode_value]
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
    
    return False


# Função para atualizar o formato dos QR codes (se necessário)
def update_qrcodes_format():
    """Atualiza o formato do arquivo qrcodes.json para o novo formato com produtos e itens."""
    qrcodes = get_qrcodes()
    updated = False
    
    # Para cada QR code no arquivo
    for qrcode, data in qrcodes.items():
        # Se o valor for apenas uma string (nome da célula)
        if isinstance(data, str):
            # Atualizar para o novo formato
            qrcodes[qrcode] = {
                "cell_name": data,
                "products": []  # Lista vazia de produtos
            }
            updated = True
    
    # Salvar se houve alguma atualização
    if updated:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
    
    return updated

# Função para adicionar ou atualizar produto em uma célula
def add_product_to_cell(cell_name, product_code, product_name):
    """Adiciona um produto a uma célula específica.
    
    Args:
        cell_name: Nome da célula
        product_code: Código do produto
        product_name: Nome do produto
        
    Returns:
        bool: True se adicionado com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    found = False
    
    # Encontrar a célula pelo nome
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict) and data.get("cell_name") == cell_name:
            # Garantir que há uma lista de produtos
            if "products" not in data:
                data["products"] = []
                
            # Verificar se o produto já existe
            product_exists = False
            for product in data["products"]:
                if product.get("code") == product_code:
                    # Atualizar nome se necessário
                    if product.get("name") != product_name:
                        product["name"] = product_name
                    product_exists = True
                    break
                    
            # Adicionar novo produto se não existir
            if not product_exists:
                data["products"].append({
                    "code": product_code,
                    "name": product_name,
                    "items": []  # Lista vazia de itens
                })
                
            found = True
            break
    
    # Salvar mudanças se encontrou a célula
    if found:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
        
    return False

# Função para adicionar item a um produto em uma célula
def add_item_to_product(cell_name, product_code, item_code, item_name):
    """Adiciona um item a um produto de uma célula específica.
    
    Args:
        cell_name: Nome da célula
        product_code: Código do produto
        item_code: Código do item
        item_name: Nome do item
        
    Returns:
        bool: True se adicionado com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    found = False
    
    # Encontrar a célula pelo nome
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict) and data.get("cell_name") == cell_name:
            # Encontrar o produto pelo código
            for product in data.get("products", []):
                if product.get("code") == product_code:
                    # Garantir que há uma lista de itens
                    if "items" not in product:
                        product["items"] = []
                        
                    # Verificar se o item já existe
                    item_exists = False
                    for item in product["items"]:
                        if item.get("code") == item_code:
                            # Atualizar nome se necessário
                            if item.get("name") != item_name:
                                item["name"] = item_name
                            item_exists = True
                            break
                            
                    # Adicionar novo item se não existir
                    if not item_exists:
                        product["items"].append({
                            "code": item_code,
                            "name": item_name
                        })
                        
                    found = True
                    break
                    
            break
    
    # Salvar mudanças se encontrou a célula e o produto
    if found:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
        
    return False

# Função para obter todos os produtos de uma célula
def get_cell_products(cell_name):
    """Obtém todos os produtos de uma célula específica.
    
    Args:
        cell_name: Nome da célula
        
    Returns:
        list: Lista de produtos da célula ou lista vazia se não encontrar
    """
    if not cell_name:
        logging.warning("Nome da célula está vazio, retornando lista vazia")
        return []
        
    qrcodes = get_qrcodes()
    
    # Log para diagnóstico extensivo
    logging.info(f"Buscando produtos para célula: {cell_name}")
    
    # Verificação de segurança para o arquivo qrcodes.json
    if not qrcodes:
        logging.warning("Arquivo qrcodes.json está vazio ou não existe")
        return []
    
    try:
        logging.debug(f"Estrutura de qrcodes.json: {json.dumps(qrcodes, indent=2)[:200]}...")
        logging.debug(f"Chaves disponíveis no primeiro nível: {list(qrcodes.keys())}")
    except Exception as e:
        logging.error(f"Erro ao analisar qrcodes.json: {str(e)}")
    
    # Busca direta pela chave exata no dicionário
    if cell_name in qrcodes:
        cell_data = qrcodes[cell_name]
        logging.debug(f"Dados encontrados para célula {cell_name} diretamente: {json.dumps(cell_data, indent=2)}")
        
        if isinstance(cell_data, dict):
            products = cell_data.get("products", [])
            logging.debug(f"Produtos encontrados diretamente: {json.dumps(products, indent=2)}")
            if products:
                logging.debug(f"Produtos encontrados diretamente para célula {cell_name}: {len(products)}")
                return products
    
    # Busca por correspondência entre cell_name e data.cell_name (pode ser que a chave seja o código QR diferente do nome da célula)
    logging.debug(f"Buscando por correspondência entre cell_name={cell_name} e data.cell_name em todos os QR codes")
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict):
            data_cell_name = str(data.get("cell_name", ""))
            logging.debug(f"Verificando QR {qrcode} com cell_name={data_cell_name}")
            if data_cell_name and data_cell_name == str(cell_name):
                products = data.get("products", [])
                logging.debug(f"Produtos encontrados via QR {qrcode}: {json.dumps(products, indent=2)}")
                if products:
                    logging.debug(f"Produtos encontrados para célula {cell_name} via QR code {qrcode}: {len(products)}")
                    return products
    
    # Busca por correspondência parcial como último recurso
    logging.debug(f"Tentando busca por correspondência parcial para {cell_name}")
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict):
            data_cell_name = str(data.get("cell_name", ""))
            if data_cell_name and (str(cell_name) in data_cell_name or data_cell_name in str(cell_name)):
                products = data.get("products", [])
                if products:
                    logging.debug(f"Produtos encontrados para célula {cell_name} por correspondência parcial com {data_cell_name}: {len(products)}")
                    return products
            
    logging.debug(f"Nenhum produto encontrado para célula {cell_name}")
    return []

# Função para obter todos os itens de um produto em uma célula
def get_product_items(cell_name, product_code):
    """Obtém todos os itens de um produto específico em uma célula.
    
    Args:
        cell_name: Nome da célula
        product_code: Código do produto
        
    Returns:
        list: Lista de itens do produto ou lista vazia se não encontrar
    """
    if not cell_name or not product_code:
        logging.debug("Nome da célula ou código do produto está vazio, retornando lista vazia")
        return []
        
    qrcodes = get_qrcodes()
    logging.debug(f"Buscando itens para célula: {cell_name}, produto: {product_code}")
    
    # Primeiro tentamos encontrar a célula
    cell_data = None
    
    # Busca direta pela chave exata no dicionário
    if cell_name in qrcodes:
        cell_data = qrcodes[cell_name]
        logging.debug(f"Dados encontrados para célula {cell_name} diretamente")
    else:
        # Busca por correspondência entre cell_name e data.cell_name
        for qrcode, data in qrcodes.items():
            if isinstance(data, dict):
                data_cell_name = str(data.get("cell_name", ""))
                if data_cell_name and data_cell_name == str(cell_name):
                    cell_data = data
                    logging.debug(f"Dados encontrados para célula {cell_name} via QR code {qrcode}")
                    break
        
        # Busca por correspondência parcial como último recurso
        if not cell_data:
            for qrcode, data in qrcodes.items():
                if isinstance(data, dict):
                    data_cell_name = str(data.get("cell_name", ""))
                    if data_cell_name and (str(cell_name) in data_cell_name or data_cell_name in str(cell_name)):
                        cell_data = data
                        logging.debug(f"Dados encontrados para célula {cell_name} por correspondência parcial")
                        break
    
    # Se encontramos a célula, procuramos o produto
    if cell_data and isinstance(cell_data, dict):
        for product in cell_data.get("products", []):
            if str(product.get("code")) == str(product_code):
                items = product.get("items", [])
                logging.debug(f"Itens encontrados para produto {product_code}: {len(items)}")
                return items
    
    logging.debug(f"Nenhum item encontrado para o produto {product_code} na célula {cell_name}")
    return []

# Função para listar todas as células cadastradas
def get_all_cells():
    """Obtém todas as células cadastradas no sistema.
    
    Returns:
        list: Lista com informações de todas as células
    """
    qrcodes = get_qrcodes()
    cells = []
    
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict):
            cell_info = {
                "qrcode": qrcode,
                "cell_name": data.get("cell_name"),
                "product_count": len(data.get("products", []))
            }
            cells.append(cell_info)
        elif isinstance(data, str):
            # Formato antigo, adicionar com contagem zero
            cell_info = {
                "qrcode": qrcode,
                "cell_name": data,
                "product_count": 0
            }
            cells.append(cell_info)
            
    return cells

# Função para remover um produto de uma célula
def remove_product_from_cell(cell_name, product_code):
    """Remove um produto de uma célula específica.
    
    Args:
        cell_name: Nome da célula
        product_code: Código do produto
        
    Returns:
        bool: True se removido com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    found = False
    
    # Encontrar a célula pelo nome
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict) and data.get("cell_name") == cell_name:
            # Filtrar produtos para remover o produto específico
            if "products" in data:
                data["products"] = [p for p in data["products"] if p.get("code") != product_code]
                found = True
            break
    
    # Salvar mudanças se encontrou a célula
    if found:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
        
    return False

# Função para remover um item de um produto
def remove_item_from_product(cell_name, product_code, item_code):
    """Remove um item de um produto em uma célula específica.
    
    Args:
        cell_name: Nome da célula
        product_code: Código do produto
        item_code: Código do item
        
    Returns:
        bool: True se removido com sucesso, False caso contrário
    """
    qrcodes = get_qrcodes()
    found = False
    
    # Encontrar a célula pelo nome
    for qrcode, data in qrcodes.items():
        if isinstance(data, dict) and data.get("cell_name") == cell_name:
            # Encontrar o produto pelo código
            for product in data.get("products", []):
                if product.get("code") == product_code:
                    # Filtrar itens para remover o item específico
                    if "items" in product:
                        product["items"] = [i for i in product["items"] if i.get("code") != item_code]
                        found = True
                    break
            break
    
    # Salvar mudanças se encontrou a célula e o produto
    if found:
        with open(os.path.join(DATA_DIR, "qrcodes.json"), 'w') as f:
            json.dump(qrcodes, f)
        return True
        
    return False

def get_cell_name(qrcode_value):
    """Get the cell name associated with a QR code."""
    if not qrcode_value:
        logging.error("get_cell_name: QR code value está vazio")
        return None
        
    logging.info(f"get_cell_name: Buscando célula para QR code {qrcode_value}")
    qrcodes = get_qrcodes()
    
    # Verificar se qrcodes é um dicionário válido
    if not isinstance(qrcodes, dict):
        logging.error(f"get_cell_name: QR codes data is not a dictionary: {type(qrcodes)}")
        return None
        
    # Log para diagnóstico
    try:
        qrcode_keys = list(qrcodes.keys())
        logging.debug(f"get_cell_name: QR codes disponíveis: {qrcode_keys[:5]}...")
        logging.debug(f"get_cell_name: Total de QR codes: {len(qrcode_keys)}")
    except Exception as e:
        logging.error(f"get_cell_name: Erro ao listar QR codes: {str(e)}")
    
    # Verificar se o QR code existe - tentativa com valor exato
    cell_data = qrcodes.get(qrcode_value)
    
    # Se não encontrou com valor exato, tentar com string
    if cell_data is None and str(qrcode_value) != qrcode_value:
        logging.debug(f"get_cell_name: Tentando com valor string: {str(qrcode_value)}")
        cell_data = qrcodes.get(str(qrcode_value))
        
    # Se ainda não encontrou, tentar outras opções de formatação
    if cell_data is None:
        # Tentar formar o QR code sem zeros à esquerda
        try:
            qrcode_int = int(qrcode_value)
            qrcode_no_leading_zeros = str(qrcode_int)
            logging.debug(f"get_cell_name: Tentando sem zeros à esquerda: {qrcode_no_leading_zeros}")
            cell_data = qrcodes.get(qrcode_no_leading_zeros)
        except (ValueError, TypeError):
            pass
    
    if cell_data is None:
        logging.error(f"get_cell_name: QR code {qrcode_value} não encontrado no sistema")
        return None
        
    # Verificar o formato do valor retornado
    if isinstance(cell_data, str):
        # Formato antigo: qrcodes[qrcode_value] = "nome_da_celula"
        logging.debug(f"get_cell_name: QR code {qrcode_value} maps to cell (old format): {cell_data}")
        return cell_data
    elif isinstance(cell_data, dict) and "cell_name" in cell_data:
        # Formato novo: qrcodes[qrcode_value] = {"cell_name": "nome_da_celula", "products": [...]}
        logging.debug(f"get_cell_name: QR code {qrcode_value} maps to cell (new format): {cell_data['cell_name']}")
        
        # Verificar se há produtos cadastrados
        products = cell_data.get("products", [])
        logging.debug(f"get_cell_name: Célula {cell_data['cell_name']} tem {len(products)} produtos cadastrados")
        
        return cell_data["cell_name"]
    else:
        logging.error(f"get_cell_name: Unknown cell format for QR code {qrcode_value}: {type(cell_data)}")
        return None

def save_setup(cell_name, order_number, supplier_name, photo_data, observation, verification_check, product_code=None, product_name=None, product_po=None, selected_items=None, setup_type="supply"):
    """Save setup data to a text file and the photo as an image file.
    
    Args:
        cell_name: Nome da célula de produção
        order_number: Número da ordem de produção
        supplier_name: Nome do abastecedor
        photo_data: Dados da foto em base64 (string única ou lista de strings)
        observation: Observações
        verification_check: Se a verificação foi realizada
        product_code: (Opcional) Código do produto selecionado (apenas para abastecimento)
        product_name: (Opcional) Nome do produto selecionado (apenas para abastecimento)
        product_po: (Opcional) PO do fornecedor para o produto (apenas para abastecimento)
        selected_items: (Opcional) Lista de itens selecionados com seus POs de fornecedor (apenas para abastecimento)
        setup_type: Tipo de setup ('removal' para retirada, 'supply' para abastecimento)
    """
    if not cell_name or not order_number or not supplier_name:
        logging.error("Missing required setup data")
        return False, "Campos obrigatórios não informados"
    
    # Diretório da célula
    cell_dir = os.path.join(DATA_DIR, cell_name)
    ensure_dir(cell_dir)
    
    # Timestamp
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Identificador único do arquivo baseado na data e hora
    file_identifier = f"{order_number}_{setup_type}_{timestamp}"
    
    # Criar um objeto de dados para salvar
    data = {
        "order_number": order_number,
        "supplier_name": supplier_name,
        "timestamp": timestamp,
        "observation": observation,
        "verification_check": verification_check,
        "setup_type": setup_type,
        "audited": False,  # Inicialmente não auditado
        "images": [],  # Array para armazenar múltiplas imagens
        "has_image": False  # Flag para indicar se tem pelo menos uma imagem
    }
    
    # Adicionar informações de produto e itens apenas para abastecimento
    if setup_type == "supply" and product_code and product_name:
        data["product_code"] = product_code
        data["product_name"] = product_name
        
        # Adicionar PO do fornecedor para o produto se houver
        if product_po:
            data["product_po"] = product_po
        
        # Adicionar itens selecionados se houver
        # Verificação e conversão para garantir que selected_items é uma lista válida
        if selected_items:
            if isinstance(selected_items, str):
                try:
                    # Tenta converter de string JSON para lista
                    data["selected_items"] = json.loads(selected_items)
                except json.JSONDecodeError:
                    data["selected_items"] = []
            elif isinstance(selected_items, list):
                data["selected_items"] = selected_items
            else:
                data["selected_items"] = []
        else:
            data["selected_items"] = []
            
        # Adicionar log para debug do array de itens
        logging.debug(f"Itens selecionados para salvar: {data.get('selected_items', [])}")
    
    # Caminho completo do arquivo de texto
    txt_path = os.path.join(cell_dir, f"{file_identifier}.txt")
    
    # Diretório para as imagens
    images_dir = os.path.join(cell_dir, file_identifier)
    ensure_dir(images_dir)
    
    # Processar dados de fotos
    if photo_data:
        # Garantir que photo_data seja uma lista
        if not isinstance(photo_data, list):
            photo_data = [photo_data]
        
        # Processar cada foto na lista
        for index, photo_base64 in enumerate(photo_data):
            try:
                # Extrair apenas os dados da imagem (remover o cabeçalho se estiver presente)
                if ',' in photo_base64:
                    photo_base64 = photo_base64.split(',')[1]
                
                # Decodificar os dados da imagem
                photo_bytes = base64.b64decode(photo_base64)
                
                # Nome do arquivo da foto
                photo_filename = f"image_{index+1}.jpg"
                photo_path = os.path.join(images_dir, photo_filename)
                
                # Abrir a imagem a partir dos bytes
                img = Image.open(BytesIO(photo_bytes))
                
                # Converter para RGB se estiver em modo P (palette) ou outros modos
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionar se a imagem for muito grande
                max_size = (1200, 1200)
                img.thumbnail(max_size, Image.LANCZOS)
                
                # Salvar com qualidade reduzida
                img.save(photo_path, format='JPEG', optimize=True, quality=85)
                
                # Adicionar informação da imagem ao array de imagens
                data["images"].append({
                    "filename": photo_filename,
                    "path": os.path.join(file_identifier, photo_filename)
                })
                
            except Exception as e:
                logging.error(f"Error saving photo {index+1}: {e}")
                # Não falhar completamente só por causa da foto
        
        # Definir que tem imagem se pelo menos uma foi salva com sucesso
        data["has_image"] = len(data["images"]) > 0
        
        # Garantir que main_image está definido
        if data["has_image"] and not data.get("main_image") and data["images"]:
            data["main_image"] = data["images"][0]["path"]
            
        # Converter formato antigo para novo, se necessário
        img_path = os.path.join(cell_dir, f"{file_identifier}.jpg")
        if os.path.exists(img_path) and not data["images"]:
            try:
                # Mover a imagem antiga para o novo formato
                photo_filename = "image_1.jpg"
                new_path = os.path.join(images_dir, photo_filename)
                
                # Usar PIL para ler e salvar a imagem
                img = Image.open(img_path)
                img.save(new_path, format='JPEG', optimize=True, quality=85)
                
                # Adicionar informação da imagem ao array de imagens
                data["images"].append({
                    "filename": photo_filename,
                    "path": os.path.join(file_identifier, photo_filename)
                })
                
                data["main_image"] = os.path.join(file_identifier, photo_filename)
                data["has_image"] = True
                
                # Remover a imagem antiga
                os.remove(img_path)
            except Exception as e:
                logging.error(f"Error converting old image format: {e}")
    
    # Salvar os dados no arquivo de texto
    try:
        with open(txt_path, 'w') as f:
            json.dump(data, f)
        return True, "Setup registrado com sucesso"
    except Exception as e:
        logging.error(f"Error saving setup data: {e}")
        return False, f"Erro ao salvar dados do setup: {str(e)}"
def get_all_setups():
    """Get all setup data organized by cells."""
    cells = {}
    
    # Iterate through cell directories
    for item in os.listdir(DATA_DIR):
        cell_dir = os.path.join(DATA_DIR, item)
        if os.path.isdir(cell_dir) and item not in ["__pycache__"]:
            cells[item] = []
            
            # Iterate through text files in each cell directory
            for file in os.listdir(cell_dir):
                if file.endswith(".txt") and not file.startswith('reset_'):
                    # O nome do arquivo agora inclui o tipo de setup (order_number_setup_type.txt)
                    file_basename = file.split(".")[0]
                    
                    # Verificar se o arquivo segue o novo formato (com tipo de setup)
                    if "_" in file_basename:
                        order_number, setup_type = file_basename.rsplit("_", 1)
                    else:
                        # Compatibilidade com arquivos antigos (sem tipo de setup)
                        order_number = file_basename
                        setup_type = "supply"  # Assumir que setups antigos são do tipo abastecimento
                    
                    txt_path = os.path.join(cell_dir, file)
                    
                    # Load setup data from text file
                    try:
                        with open(txt_path, 'r') as f:
                            setup_data = json.load(f)
                        
                        # Adicionar tipo de setup se não existir no dado carregado
                        if "setup_type" not in setup_data:
                            setup_data["setup_type"] = setup_type
                            
                        # Garantir que o campo audited é um booleano
                        if "audited" in setup_data:
                            if isinstance(setup_data["audited"], str):
                                setup_data["audited"] = setup_data["audited"].lower() in ['true', 'yes', '1', 'on']
                            setup_data["audited"] = bool(setup_data["audited"])
                        
                        # Garantir que file_identifier está disponível para referência posterior
                        setup_data["file_identifier"] = file_basename
                        
                        # Verificar imagens no novo formato (múltiplas imagens)
                        if "images" in setup_data and isinstance(setup_data["images"], list) and len(setup_data["images"]) > 0:
                            # Novo formato com múltiplas imagens
                            setup_data["has_image"] = True
                            # Garantir que a primeira imagem é a principal para compatibilidade
                            setup_data["main_image"] = setup_data["images"][0]["path"] if setup_data["images"] else ""
                        else:
                            # Verificar formato antigo (imagem única)
                            img_path = os.path.join(cell_dir, f"{file_basename}.jpg")
                            if os.path.exists(img_path):
                                setup_data["has_image"] = True
                                # Converter formato antigo para o novo
                                setup_data["images"] = [{
                                    "filename": f"{file_basename}.jpg",
                                    "path": f"{file_basename}.jpg"
                                }]
                                setup_data["main_image"] = f"{file_basename}.jpg"
                            else:
                                # Verificar pasta de imagens
                                images_dir = os.path.join(cell_dir, file_basename)
                                if os.path.isdir(images_dir):
                                    # Procurar por imagens na pasta
                                    image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                                    if image_files:
                                        setup_data["has_image"] = True
                                        setup_data["images"] = []
                                        for img_file in image_files:
                                            setup_data["images"].append({
                                                "filename": img_file,
                                                "path": os.path.join(file_basename, img_file)
                                            })
                                        setup_data["main_image"] = os.path.join(file_basename, image_files[0])
                                    else:
                                        setup_data["has_image"] = False
                                        setup_data["images"] = []
                                else:
                                    setup_data["has_image"] = False
                                    setup_data["images"] = []
                        
                        cells[item].append(setup_data)
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        logging.error(f"Error loading setup data from {txt_path}: {e}")
    
    return cells

def update_setup(cell_name, order_number, supplier_name, observation, verification_check, audited=None, auditor_name=None, setup_type=None, photo_data=None, timestamp=None, audit_notes=None):
    """Update an existing setup data file."""
    # Adicionar log detalhado dos dados recebidos
    logging.debug(f"Atualizando setup: cell_name={cell_name}, order_number={order_number}, supplier_name={supplier_name}, observation={observation}, verification_check={verification_check}, setup_type={setup_type}")
    
    # Normalizar o valor de verification_check para booleano
    if isinstance(verification_check, str):
        verification_check = verification_check.lower() in ['true', 'on', '1', 'yes']
    # Diretório da célula
    cell_dir = os.path.join(DATA_DIR, cell_name)
    
    if not os.path.isdir(cell_dir):
        logging.error(f"Diretório da célula não encontrado: {cell_dir}")
        return False
    
    # Procurar por arquivos que correspondam ao padrão
    text_file_path = None
    
    # Se temos um tipo de setup específico, vamos procurar arquivos com esse padrão
    if setup_type:
        prefix = f"{order_number}_{setup_type}"
        matching_files = []
        
        for file in os.listdir(cell_dir):
            if file.endswith(".txt") and file.startswith(prefix):
                matching_files.append(file)
        
        if matching_files:
            # Ordenar os arquivos por ordem alfabética (o mais recente será o último)
            matching_files.sort()
            # Usar o arquivo mais recente
            text_file_path = os.path.join(cell_dir, matching_files[-1])
            logging.debug(f"Arquivo encontrado para atualização: {text_file_path}")
        else:
            logging.error(f"Nenhum arquivo encontrado com padrão {prefix}*.txt na célula {cell_name}")
            return False
    else:
        # Se não temos o tipo, vamos procurar arquivos com esse order_number
        matching_files = []
        
        for file in os.listdir(cell_dir):
            if file.endswith(".txt") and file.startswith(f"{order_number}_"):
                matching_files.append(file)
        
        if matching_files:
            # Ordenar os arquivos por ordem alfabética (o mais recente será o último)
            matching_files.sort()
            # Usar o arquivo mais recente
            text_file_path = os.path.join(cell_dir, matching_files[-1])
            logging.debug(f"Arquivo encontrado para atualização (sem tipo especificado): {text_file_path}")
        else:
            logging.error(f"Nenhum arquivo encontrado para order_number={order_number} na célula {cell_name}")
            return False
    
    try:
        with open(text_file_path, 'r') as f:
            data = json.load(f)
        
        # Log dos dados atuais antes da atualização
        logging.debug(f"Dados antes da atualização: supplier_name={data.get('supplier_name', '')}, observation={data.get('observation', '')}")
        
        # Update fields
        data["supplier_name"] = supplier_name if supplier_name is not None else data.get("supplier_name", "")
        data["observation"] = observation
        data["verification_check"] = verification_check
        
        # Log depois da atualização
        logging.debug(f"Dados após atualização: supplier_name={data.get('supplier_name', '')}, observation={data.get('observation', '')}")
        
        # Atualizar o timestamp se fornecido
        if timestamp:
            data["timestamp"] = timestamp
        
        # Update audit fields if provided
        if audited is not None:
            data["audited"] = audited
            # Se estiver marcando como auditado, sempre definir timestamp da auditoria atual
            if audited:
                data["audit_timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Se estiver desmarcando, remover o timestamp da auditoria
            elif not audited and data.get("audit_timestamp"):
                data.pop("audit_timestamp", None)

        if auditor_name is not None:
            data["auditor_name"] = auditor_name
            
        # Adicionar anotações de auditoria, se fornecidas
        if audit_notes is not None:
            data["audit_notes"] = audit_notes
        
        # Garantir que o setup_type está definido
        if setup_type and "setup_type" not in data:
            data["setup_type"] = setup_type
        
        # Atualizar a foto se fornecida
        if photo_data:
            cell_dir = os.path.join(DATA_DIR, cell_name)
            file_identifier = f"{order_number}_{data.get('setup_type', 'supply')}"
            
            # Verificar se photo_data é uma string única ou uma lista
            if isinstance(photo_data, str):
                photo_data_list = [photo_data]
            elif isinstance(photo_data, list):
                photo_data_list = photo_data
            else:
                photo_data_list = []
            
            # Processar apenas a primeira imagem no formato antigo
            if photo_data_list:
                photo_item = photo_data_list[0]
                # Remove the "data:image/jpeg;base64," part
                if "base64," in photo_item:
                    photo_item = photo_item.split("base64,")[1]
                    
                try:
                    # Decode photo data
                    photo_bytes = base64.b64decode(photo_item)
                    photo_path = os.path.join(cell_dir, f"{file_identifier}.jpg")
                    
                    # Processar imagem para reduzir tamanho
                    from PIL import Image
                    from io import BytesIO
                    
                    # Abrir a imagem a partir dos bytes
                    img = Image.open(BytesIO(photo_bytes))
                    
                    # Converter para RGB se estiver em modo P (palette) ou outros modos
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Redimensionar se a imagem for muito grande
                    max_size = (1200, 1200)
                    img.thumbnail(max_size, Image.LANCZOS)
                    
                    # Salvar com qualidade reduzida
                    img.save(photo_path, format='JPEG', optimize=True, quality=85)
                    
                    # Marcar que tem imagem
                    data["has_image"] = True
                    
                except Exception as e:
                    logging.error(f"Error saving photo: {e}")
                    # Não falhar completamente só por causa da foto
        
        # Registrar conteúdo antes de salvar
        logging.debug(f"Dados finais antes de salvar: observation={data.get('observation', '(vazio)')}")
        
        # Salvar arquivo
        with open(text_file_path, 'w') as f:
            json.dump(data, f)
            
        # Verificar se o arquivo foi salvo corretamente
        try:
            with open(text_file_path, 'r') as f:
                saved_data = json.load(f)
                logging.debug(f"Verificação após salvar: observation={saved_data.get('observation', '(não encontrado)')}")
        except Exception as e:
            logging.error(f"Erro ao verificar arquivo salvo: {e}")
            
        return True
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error updating setup: {e}")
        return False

# Rota para atualizar o formato dos QR codes
@app.route('/update_qrcodes_format')
def update_qrcodes_format_route():
    """Atualiza o formato dos QR codes para o novo formato com produtos."""
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        flash('Acesso restrito. Apenas auditores podem acessar esta função.', 'danger')
        return redirect(url_for('index'))
    
    try:
        updated = update_qrcodes_format()
        if updated:
            flash('Formato dos QR codes atualizado com sucesso!', 'success')
        else:
            flash('Os QR codes já estão no formato mais recente.', 'info')
    except Exception as e:
        logging.error(f"Erro ao atualizar formato dos QR codes: {e}")
        flash(f'Erro ao atualizar formato dos QR codes: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/')
def index():
    """Render the home page."""
    username = session.get('username')
    user_profile = 'visitor'  # Default perfil para não logados
    
    if username:
        users = get_users()
        user_profile = users.get(username, {}).get('profile', 'visitor')
    
    return render_template('index.html', user_profile=user_profile)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logging.debug(f"Login attempt: username={username}")
        
        if authenticate_user(username, password):
            logging.debug(f"Login successful for user: {username}")
            session['logged_in'] = True
            session['username'] = username
            
            # Add debug flash message for successful login
            flash(f'Login bem-sucedido como {username}', 'success')
            
            next_page = request.args.get('next') or url_for('index')
            logging.debug(f"Redirecting to: {next_page}")
            return redirect(next_page)
        else:
            # Log login failure
            logging.debug(f"Login failed for user: {username}")
            flash('Usuário ou senha inválidos', 'danger')
    
    return render_template('login.html')

@app.route('/cadastro_usuarios', methods=['GET', 'POST'])
def cadastro_usuarios():
    """Gerenciar usuários do sistema."""
    # Verificar se o usuário está logado
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        flash('Acesso restrito. Apenas auditores podem acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # Adicionar novo usuário
            username = request.form.get('username')
            password = request.form.get('password')
            profile = request.form.get('profile', 'auditor')  # Valor padrão é auditor
            
            if not username or not password:
                flash('Usuário e senha são obrigatórios', 'danger')
                return redirect(url_for('cadastro_usuarios'))
            
            # Verificar se o usuário já existe
            users = get_users()
            if username in users:
                flash(f'Usuário {username} já existe', 'warning')
            else:
                add_user(username, password, profile)
                flash(f'Usuário {username} adicionado com sucesso', 'success')
                
        elif action == 'edit':
            # Editar usuário existente (senha e perfil)
            username = request.form.get('username')
            new_password = request.form.get('new_password')
            profile = request.form.get('edit_profile')  # Novo campo para o perfil na edição
            
            if not username or not new_password:
                flash('Nome de usuário e nova senha são obrigatórios', 'danger')
                return redirect(url_for('cadastro_usuarios'))
            
            # Se não foi enviado um perfil, manter o perfil atual
            if not profile:
                users = get_users()
                if username in users:
                    profile = users[username].get('profile', 'auditor')
            
            add_user(username, new_password, profile)
            flash(f'Usuário {username} atualizado com sucesso', 'success')
            
        elif action == 'delete':
            # Excluir usuário
            username = request.form.get('username')
            
            # Não permitir excluir o próprio usuário
            if username == session.get('username'):
                flash('Você não pode excluir seu próprio usuário', 'danger')
                return redirect(url_for('cadastro_usuarios'))
            
            if delete_user(username):
                flash(f'Usuário {username} excluído com sucesso', 'success')
            else:
                flash(f'Não foi possível excluir o usuário {username}', 'danger')
    
    # Obter lista atualizada de usuários
    users = get_users()
    return render_template('user_management.html', users=users)

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/setup', methods=['GET', 'POST'])
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Handle setup registration."""
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if request.method == 'POST':
        # Obter dados do formulário
        cell_name = request.form.get('cell_name')
        order_number = request.form.get('order_number')
        supplier_name = request.form.get('supplier_name') or username
        observation = request.form.get('observation', '')
        verification_check = request.form.get('verification_check', '') in ['on', 'true', 'True', '1']
        setup_type = request.form.get('setup_type', 'supply')
        photo_data_json = request.form.get('photo_data', '')
        
        # Obter dados específicos de produto e itens (para tipo de setup 'supply')
        product_code = request.form.get('product_code')
        product_name = request.form.get('product_name')
        product_po = request.form.get('product_po')  # PO do fornecedor para o produto
        selected_items_json = request.form.get('selected_items')
        selected_items = []
        
        if selected_items_json:
            try:
                selected_items = json.loads(selected_items_json)
            except json.JSONDecodeError:
                selected_items = []
        
        # Validação básica
        required_fields = [cell_name, order_number]
        
        # Para todos os tipos, verificar o nome do abastecedor
        if not supplier_name:
            supplier_name = username
            required_fields.append(supplier_name)
            
        # Obter QR code da célula atual
        cell_qrcode = request.form.get('qrcode_value')
        
        # Validação básica para todos os tipos
        if not all(required_fields):
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return redirect(url_for('setup', qrcode=cell_qrcode))
        
        # Validação específica para abastecimento
        if setup_type == 'supply':
            # Produto é obrigatório para operações de abastecimento
            if not product_code or not product_name:
                flash('Para registros de abastecimento, é obrigatório selecionar um produto.', 'danger')
                return redirect(url_for('setup', qrcode=cell_qrcode))
        elif setup_type == 'removal':
            # Para retirada, produto e itens não são obrigatórios
            # Garantir que esses campos não causem problemas quando não preenchidos
            product_code = None
            product_name = None
            product_po = None
            selected_items = []
        
        # Converter string JSON para lista de imagens, se for JSON
        try:
            if photo_data_json.startswith('[') and photo_data_json.endswith(']'):
                photo_data = json.loads(photo_data_json)
            else:
                # Se não for JSON, tratar como string única (formato antigo)
                photo_data = photo_data_json
        except json.JSONDecodeError:
            # Se houve erro no parsing JSON, usar o texto original
            photo_data = photo_data_json
        
        # Save setup data com tipo específico e informações de produto/itens
        save_result, message = save_setup(
            cell_name, 
            order_number, 
            supplier_name, 
            photo_data, 
            observation, 
            verification_check,
            product_code=product_code if setup_type == 'supply' else None,
            product_name=product_name if setup_type == 'supply' else None,
            product_po=product_po if setup_type == 'supply' else None,
            selected_items=selected_items if setup_type == 'supply' else None,
            setup_type=setup_type
        )
        
        if save_result:
            # Mensagem de sucesso específica para o tipo de setup
            if setup_type == 'removal':
                flash('Retirada de material registrada com sucesso!', 'success')
            else:
                flash('Abastecimento de material registrado com sucesso!', 'success')
        else:
            flash(f'Erro ao registrar setup: {message}', 'danger')
            
        return redirect(url_for('index'))
    
    qrcode = request.args.get('qrcode')
    cell_name = get_cell_name(qrcode) if qrcode else None
    
    # Obter lista de produtos disponíveis para a célula
    cell_products = []
    
    if qrcode:
        # Vamos primeiro obter o nome da célula a partir do QR code
        cell_name = get_cell_name(qrcode)
        logging.debug(f"QR code {qrcode} maps to cell: {cell_name}")
        
        if cell_name:
            # Vamos tentar uma abordagem diferente para obter produtos diretamente do JSON
            qrcodes = get_qrcodes()
            if qrcode in qrcodes:
                qrcode_data = qrcodes[qrcode]
                logging.debug(f"Dados encontrados para QR code {qrcode}: {json.dumps(qrcode_data, indent=2)}")
                
                if isinstance(qrcode_data, dict) and "products" in qrcode_data:
                    cell_products = qrcode_data["products"]
                    logging.debug(f"Produtos obtidos diretamente do QR code {qrcode}: {len(cell_products)}")
                else:
                    logging.debug(f"O QR code {qrcode} não tem produtos ou formato inválido")
            
            # Se não encontrou produtos diretamente, tentar pelo nome da célula
            if not cell_products:
                logging.debug(f"Tentando obter produtos pelo nome da célula {cell_name}")
                cell_products = get_cell_products(cell_name)
                logging.debug(f"Produtos obtidos pelo nome da célula {cell_name}: {len(cell_products)}")
        else:
            logging.warning(f"QR code {qrcode} não encontrado nos dados")
    else:
        logging.debug("Nenhum QR code fornecido")
    
    logging.debug(f"Produtos passados para o template: {json.dumps(cell_products, indent=2)}")
    
    return render_template('setup.html', 
                          qrcode=qrcode, 
                          cell_name=cell_name, 
                          user_profile=user_profile, 
                          username=username,
                          cell_products=cell_products)
def check_setup_status():
    """API para verificar o status dos setups para uma célula e ordem de produção específica.
    
    Verifica se já existem registros de retirada e abastecimento para a ordem.
    """
    cell_name = request.args.get('cell_name')
    order_number = request.args.get('order_number')
    
    if not all([cell_name, order_number]):
        return jsonify({
            "success": False,
            "message": "Célula e número de ordem são obrigatórios",
            "has_removal": False,
            "has_supply": False
        }), 400
    
    # Verificar arquivos para a ordem na célula
    cell_dir = os.path.join(DATA_DIR, cell_name)
    has_removal = False
    has_supply = False
    
    # Data e hora do reset mais recente (se houver)
    last_reset_timestamp = None
    
    # Verificar se houve reset recente
    resets_dir = os.path.join(cell_dir, "resets")
    if os.path.isdir(resets_dir):
        # Procurar pelo arquivo de histórico de resets
        history_file = os.path.join(resets_dir, "reset_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                # Obter o timestamp do reset mais recente
                if history and len(history) > 0:
                    # Ordenar pelo timestamp (mais recente primeiro)
                    sorted_history = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
                    last_reset = sorted_history[0]
                    last_reset_timestamp = datetime.datetime.strptime(last_reset.get('timestamp', ''), '%Y-%m-%d %H-%M-%S')
                    logging.debug(f"Reset mais recente em: {last_reset_timestamp}")
            except Exception as e:
                logging.error(f"Erro ao ler histórico de resets: {e}")
    
    # Verificar arquivos de setup específicos para esta ordem
    if os.path.isdir(cell_dir):
        for file in os.listdir(cell_dir):
            if file.endswith(".txt") and file.startswith(f"{order_number}_"):
                file_path = os.path.join(cell_dir, file)
                try:
                    # Verificar se o arquivo foi criado após o último reset
                    file_mtime = os.path.getmtime(file_path)
                    file_timestamp = datetime.datetime.fromtimestamp(file_mtime)
                    
                    # Ignorar arquivos criados antes do último reset (se houver)
                    if last_reset_timestamp and file_timestamp < last_reset_timestamp:
                        logging.debug(f"Ignorando arquivo anterior ao reset: {file}")
                        continue
                        
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    setup_type = data.get('setup_type', '')
                    if setup_type == 'removal':
                        has_removal = True
                    elif setup_type == 'supply':
                        has_supply = True
                except Exception as e:
                    logging.error(f"Erro ao ler arquivo de setup {file_path}: {e}")
    
    return jsonify({
        "success": True,
        "has_removal": has_removal,
        "has_supply": has_supply,
        "message": "Status verificado com sucesso"
    })

@app.route('/audit')
def audit():
    """Display the audit page."""
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        flash('Acesso restrito. Apenas auditores podem acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    # Obter parâmetros de filtro
    filter_date_start = request.args.get('filter_date_start', '')
    filter_date_end = request.args.get('filter_date_end', '')
    filter_auditor = request.args.get('filter_auditor', '')
    filter_audited = request.args.get('filter_audited', '')
    filter_order = request.args.get('filter_order', '')
    filter_cell = request.args.get('filter_cell', '')
    filter_supplier = request.args.get('filter_supplier', '')
    
    # Obter todos os setups
    cells = get_all_setups()
    
    # Aplicar filtros, mas manter a estrutura original para o template
    if any([filter_date_start, filter_date_end, filter_auditor, filter_audited, filter_order, filter_cell, filter_supplier]):
        filtered_cells = {}
        
        for cell_name, setups in cells.items():
            # Filtrar por nome da célula
            if filter_cell and filter_cell.lower() not in cell_name.lower():
                continue
                
            filtered_setups = []
            for setup in setups:
                # Filtrar por período de datas
                setup_date = setup.get('timestamp', '').split(' ')[0]  # Extrair apenas a parte da data (YYYY-MM-DD)
                
                # Se data inicial está especificada e a data do setup é anterior
                if filter_date_start and setup_date < filter_date_start:
                    continue
                    
                # Se data final está especificada e a data do setup é posterior
                if filter_date_end and setup_date > filter_date_end:
                    continue
                    
                # Filtrar por auditor
                if filter_auditor and filter_auditor.lower() not in setup.get('auditor_name', '').lower():
                    continue
                    
                # Filtrar por abastecedor (novo)
                if filter_supplier and filter_supplier.lower() not in setup.get('supplier_name', '').lower():
                    continue
                    
                # Filtrar por status de auditoria
                if filter_audited:
                    is_audited = setup.get('audited', False)
                    if (filter_audited == 'sim' and not is_audited) or (filter_audited == 'nao' and is_audited):
                        continue
                
                # Filtrar por ordem de produção
                if filter_order and filter_order.lower() not in setup.get('order_number', '').lower():
                    continue
                    
                filtered_setups.append(setup)
                
            if filtered_setups:
                filtered_cells[cell_name] = filtered_setups
                
        cells = filtered_cells
    
    # Garantir que todos os dados estão no formato correto
    for cell_name, setups in cells.items():
        for setup in setups:
            # Garantir que o campo audited é um booleano
            if isinstance(setup.get('audited'), str):
                setup['audited'] = setup['audited'].lower() in ['true', 'yes', '1', 'on']
            setup['audited'] = bool(setup.get('audited', False))
            
            # Garantir que selected_items é uma lista
            if 'selected_items' not in setup or setup['selected_items'] is None:
                setup['selected_items'] = []
            elif isinstance(setup.get('selected_items'), str):
                try:
                    setup['selected_items'] = json.loads(setup['selected_items'])
                except:
                    setup['selected_items'] = []
    
    # Adicionar logs para depuração dos contadores
    total_geral = 0
    auditados_geral = 0
    for cell_name, setups in cells.items():
        total_geral += len(setups)
        auditados_geral += sum(1 for setup in setups if setup.get('audited', False))
    
    logging.debug(f"Contadores gerais - Total: {total_geral}, Auditados: {auditados_geral}")
    
    return render_template('audit.html', cells=cells)

@app.route('/register_qrcode', methods=['GET', 'POST'])
def register_qrcode():
    """Handle QR code registration."""
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        flash('Acesso restrito. Apenas auditores podem acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    # Obter lista de células para exibir na página
    cells = get_all_cells()
    
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        
        if action == 'add':
            qrcode_value = request.form.get('qrcode_value')
            cell_name = request.form.get('cell_name')
            
            if not all([qrcode_value, cell_name]):
                flash('QR Code e nome da célula são obrigatórios', 'danger')
                return redirect(url_for('register_qrcode'))
            
            save_qrcode(qrcode_value, cell_name)
            flash('QR Code cadastrado com sucesso!', 'success')
            return redirect(url_for('register_qrcode'))
    
    return render_template('register_qrcode.html', cells=cells)

@app.route('/edit_qrcode', methods=['POST'])
def edit_qrcode():
    """Handle QR code update."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito"}), 403
    
    qrcode_value = request.form.get('qrcode_value')
    new_cell_name = request.form.get('new_cell_name')
    
    if not all([qrcode_value, new_cell_name]):
        return jsonify({"success": False, "message": "QR Code e nome da célula são obrigatórios"}), 400
    
    if update_qrcode(qrcode_value, new_cell_name):
        return jsonify({"success": True, "message": "QR Code atualizado com sucesso!"})
    else:
        return jsonify({"success": False, "message": "QR Code não encontrado"}), 404

@app.route('/delete_qrcode', methods=['POST'])
def delete_qrcode_route():
    """Handle QR code deletion."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito"}), 403
    
    qrcode_value = request.form.get('qrcode_value')
    
    if not qrcode_value:
        return jsonify({"success": False, "message": "QR Code é obrigatório"}), 400
    
    if delete_qrcode(qrcode_value):
        return jsonify({"success": True, "message": "QR Code excluído com sucesso!"})
    else:
        return jsonify({"success": False, "message": "QR Code não encontrado"}), 404

@app.route('/api/get_cell_name/<qrcode>')
def api_get_cell_name(qrcode):
    """API endpoint to get cell name from QR code."""
    # Permitir acesso até mesmo sem autenticação para facilitar o fluxo
    # Isso é necessário para o funcionamento do script de carregamento de produtos
    
    cell_name = get_cell_name(qrcode)
    logging.info(f"API get_cell_name: QR code={qrcode}, resultado={cell_name}")
    
    # Verificar se obteve um nome de célula válido
    if cell_name is None:
        return jsonify({"success": False, "message": "QR code não cadastrado"}), 404
        
    # Se chegou aqui, temos um nome de célula válido
    logging.debug(f"API: QR code {qrcode} maps to cell: {cell_name}")
    
    # Verificar status de setup para a célula
    setup_status = {
        "removal": False,
        "supply": False
    }
    
    # Obter último número de ordem usado na célula (se houver)
    most_recent_order = None
    
    # Data e hora do reset mais recente (se houver)
    last_reset_timestamp = None
    
    # Verificar se houve reset recente
    cell_dir = os.path.join(DATA_DIR, cell_name)
    resets_dir = os.path.join(cell_dir, "resets")
    
    if os.path.isdir(resets_dir):
        # Procurar pelo arquivo de histórico de resets
        history_file = os.path.join(resets_dir, "reset_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                
                # Obter o timestamp do reset mais recente
                if history and len(history) > 0:
                    # Ordenar pelo timestamp (mais recente primeiro)
                    sorted_history = sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
                    last_reset = sorted_history[0]
                    last_reset_timestamp = datetime.datetime.strptime(last_reset.get('timestamp', ''), '%Y-%m-%d %H-%M-%S')
                    logging.debug(f"Reset mais recente em: {last_reset_timestamp}")
            except Exception as e:
                logging.error(f"Erro ao ler histórico de resets: {e}")
    
    # Verificar os arquivos na célula para determinar o status
    if os.path.isdir(cell_dir):
        # Primeiro, procurar o número de ordem mais recente
        setup_files = []
        for file in os.listdir(cell_dir):
            if file.endswith(".txt") and not file.startswith("reset_log_"):
                file_path = os.path.join(cell_dir, file)
                try:
                    file_mtime = os.path.getmtime(file_path)
                    file_timestamp = datetime.datetime.fromtimestamp(file_mtime)
                    
                    # Ignorar arquivos criados antes do último reset (se houver)
                    if last_reset_timestamp and file_timestamp < last_reset_timestamp:
                        logging.debug(f"Ignorando arquivo anterior ao reset: {file}")
                        continue
                    
                    with open(file_path, 'r') as f:
                        setup_data = json.load(f)
                    
                    # Extrair informações relevantes para ordenação
                    order_number = setup_data.get('order_number')
                    setup_type = setup_data.get('setup_type')
                    timestamp = setup_data.get('timestamp')
                    
                    # Atualizar most_recent_order se necessário
                    if order_number and (most_recent_order is None or order_number > most_recent_order):
                        most_recent_order = order_number
                    
                    # Adicionar à lista para análise posterior
                    setup_files.append({
                        'path': file_path,
                        'order_number': order_number,
                        'setup_type': setup_type,
                        'timestamp': timestamp,
                        'file_mtime': file_mtime
                    })
                    
                except Exception as e:
                    logging.error(f"Erro ao ler arquivo de setup {file_path}: {e}")
        
        # Ordenar por timestamp (mais recente primeiro)
        setup_files.sort(key=lambda x: x['file_mtime'], reverse=True)
        
        # Filtrar apenas os arquivos da ordem mais recente, se houver
        if most_recent_order and setup_files:
            latest_order_files = [f for f in setup_files if f['order_number'] == most_recent_order]
            
            # Verificar status de setup para a ordem mais recente
            for file_info in latest_order_files:
                setup_type = file_info.get('setup_type')
                if setup_type == 'removal':
                    setup_status['removal'] = True
                elif setup_type == 'supply':
                    setup_status['supply'] = True
    
    # Retornar informações completas sobre a célula
    return jsonify({
        "success": True,
        "cell_name": cell_name,
        "setup_status": setup_status,
        "most_recent_order": most_recent_order
    })

@app.route('/api/update_setup', methods=['POST'])
def api_update_setup():
    """API endpoint to update setup data."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    logging.debug(f"API update_setup: dados recebidos = {json.dumps(data)}")
    
    # Verificar explicitamente o campo observation
    observation = data.get('observation', '')
    logging.debug(f"API update_setup: observation recebido = '{observation}'")
    
    success = update_setup(
        data.get('cell_name'),
        data.get('order_number'),
        data.get('supplier_name'),
        observation,
        data.get('verification_check', False),
        data.get('audited'),
        data.get('auditor_name'),
        data.get('setup_type'),
        data.get('photo_data'),
        data.get('timestamp')
    )
    
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Erro ao atualizar setup"}), 500

@app.route('/api/mark_as_audited', methods=['POST'])
def api_mark_as_audited():
    """API endpoint to mark or unmark a setup as audited."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Aceitar dados tanto via JSON quanto via FormData
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    # Log para debug
    logging.debug(f"API mark_as_audited: Recebido dados: {data}")
    
    auditor_name = session.get('username')
    
    # Verificar se é para marcar ou desmarcar
    audited = data.get('audited')
    is_mark_action = audited not in ['false', 'False', False, '0', 0]
    audit_notes = data.get('audit_notes', '')
    
    # Verificar se o usuário tem perfil de auditor
    users = get_users()
    user_profile = users.get(auditor_name, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Somente auditores podem alterar o status de auditoria"}), 403
    
    # Buscar os dados existentes antes de qualquer atualização
    cell_name = data.get('cell_name')
    order_number = data.get('order_number')
    setup_type = data.get('setup_type')
    
    # Diretório da célula e padrão de arquivo
    cell_dir = os.path.join(DATA_DIR, cell_name)
    prefix = f"{order_number}_{setup_type}"
    
    # Encontrar o arquivo correspondente
    text_file_path = None
    existing_data = {}
    for file in os.listdir(cell_dir):
        if file.endswith(".txt") and file.startswith(prefix):
            text_file_path = os.path.join(cell_dir, file)
            try:
                with open(text_file_path, 'r') as f:
                    existing_data = json.load(f)
                break
            except Exception as e:
                logging.error(f"Erro ao ler arquivo existente: {e}")
    
    # Se não encontrou ou não conseguiu ler os dados existentes, usar valores padrão
    supplier_name = existing_data.get('supplier_name', data.get('supplier_name', ''))
    observation = existing_data.get('observation', data.get('observation', ''))
    verification_check = existing_data.get('verification_check', False)
    
    # Se for para desmarcar, definimos como False e limpamos o nome do auditor
    if not is_mark_action:
        success = update_setup(
            cell_name,
            order_number,
            supplier_name,  # Manter o nome do abastecedor original
            observation,    # Manter a observação original
            verification_check,  # Manter o status de verificação original
            False,  # Desmarcar a auditoria
            '',     # Limpar o nome do auditor
            setup_type,
            None,   # Sem mudança na foto
            None,   # Sem mudança no timestamp
            ''      # Limpar anotações de auditoria
        )
        if success:
            return jsonify({"success": True, "audited": False, "auditor_name": "", "audit_notes": ""})
    # Caso contrário, marcamos como auditado normalmente
    else:
        success = update_setup(
            cell_name,
            order_number,
            supplier_name,  # Manter o nome do abastecedor original
            observation,    # Manter a observação original
            verification_check,  # Manter o status de verificação original
            True,  # Marcar como auditado
            auditor_name,
            setup_type,
            None,  # Sem mudança na foto
            None,  # Sem mudança no timestamp
            audit_notes  # Incluir anotações de auditoria
        )
        if success:
            return jsonify({
                "success": True, 
                "audited": True, 
                "auditor_name": auditor_name,
                "audit_notes": audit_notes
            })
    
    return jsonify({"success": False, "message": "Erro ao alterar status da auditoria"}), 500

def delete_setup(cell_name, order_number, setup_type):
    """Delete a setup entry and its related image."""
    cell_dir = os.path.join(DATA_DIR, cell_name)
    
    if not os.path.isdir(cell_dir):
        return False
    
    # Procurar por arquivos que correspondam ao padrão
    prefix = f"{order_number}_{setup_type}"
    success = False
    files_to_delete = []
    
    # Encontrar todos os arquivos TXT e JPG relacionados
    for file in os.listdir(cell_dir):
        # Encontrar arquivos de texto com o padrão correto
        if file.startswith(prefix) and file.endswith(".txt"):
            files_to_delete.append(os.path.join(cell_dir, file))
            
            # Verificar se existe um diretório de imagens com o mesmo nome (sem a extensão)
            base_name = file[:-4]  # Remover .txt
            img_dir = os.path.join(cell_dir, base_name)
            if os.path.isdir(img_dir):
                for img_file in os.listdir(img_dir):
                    if img_file.endswith(('.jpg', '.jpeg', '.png')):
                        files_to_delete.append(os.path.join(img_dir, img_file))
            
            # Para compatibilidade, verificar também o arquivo de imagem direto
            img_file = f"{base_name}.jpg"
            img_path = os.path.join(cell_dir, img_file)
            if os.path.exists(img_path):
                files_to_delete.append(img_path)
    
    if not files_to_delete:
        logging.error(f"Nenhum arquivo encontrado para exclusão: {prefix}")
        return False
    
    # Excluir todos os arquivos encontrados
    for file_path in files_to_delete:
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            success = True
        except Exception as e:
            logging.error(f"Erro ao excluir arquivo: {file_path}, erro: {e}")
    
    return success

@app.route('/api/delete_setup', methods=['POST'])
def api_delete_setup():
    """API endpoint to delete a setup entry."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem perfil de auditor
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Somente auditores podem excluir registros"}), 403
    
    # Aceitar dados tanto via JSON quanto via FormData
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    # Log para debug
    logging.debug(f"API delete_setup: Recebido dados: {data}")
    
    cell_name = data.get('cell_name')
    order_number = data.get('order_number')
    setup_type = data.get('setup_type')
    
    if not all([cell_name, order_number, setup_type]):
        return jsonify({"success": False, "message": "Dados incompletos para exclusão"}), 400
    
    success = delete_setup(cell_name, order_number, setup_type)
    
    if success:
        return jsonify({"success": True, "message": "Registro excluído com sucesso"})
    else:
        return jsonify({"success": False, "message": "Erro ao excluir o registro"}), 500

@app.route('/photos/<cell_name>/<path:filepath>')
def get_photo(cell_name, filepath):
    """Serve setup photos, including from subdirectories.
    
    Args:
        cell_name: Nome da célula
        filepath: Caminho do arquivo, pode incluir subdiretórios
    """
    cell_dir = os.path.join(DATA_DIR, cell_name)
    
    # Se filepath contém um subdiretório
    if '/' in filepath:
        subdir, filename = filepath.rsplit('/', 1)
        return send_from_directory(os.path.join(cell_dir, subdir), filename)
    else:
        # Compatibilidade com formato antigo
        return send_from_directory(cell_dir, filepath)

@app.route('/get_setup_images/<cell_name>/<order_number>/<setup_type>')
def get_setup_images(cell_name, order_number, setup_type):
    """API para obter as imagens de um setup específico.
    
    Args:
        cell_name: Nome da célula
        order_number: Número da ordem
        setup_type: Tipo de setup (supply ou removal)
        
    Returns:
        JSON com a lista de imagens disponíveis para o setup
    """
    try:
        logging.debug(f"Buscando imagens para cell={cell_name}, order={order_number}, type={setup_type}")
        cell_dir = os.path.join(DATA_DIR, cell_name)
        
        if not os.path.isdir(cell_dir):
            logging.error(f"Diretório da célula não existe: {cell_dir}")
            return jsonify({"success": False, "images": [], "error": "Diretório da célula não encontrado"})
        
        # Lista de possíveis diretórios/arquivos para verificar
        # Primeiro tentamos encontrar um diretório com o nome completo do setup (formato novo)
        # Se não encontrarmos, buscamos arquivos diretos (formato antigo)
        
        # Listar todos os arquivos no diretório da célula
        all_files = os.listdir(cell_dir)
        logging.debug(f"Arquivos encontrados na célula: {all_files}")
        
        # As imagens agora usam o timestamp como parte do nome do diretório
        # Vamos procurar diretórios que tenham ordem e tipo no nome
        matching_dirs = []
        for item in all_files:
            # Verificar se o item tem o padrão {order_number}_{setup_type}
            item_path = os.path.join(cell_dir, item)
            if os.path.isdir(item_path) and f"{order_number}_{setup_type}" in item:
                matching_dirs.append(item)
        
        logging.debug(f"Diretórios correspondentes encontrados: {matching_dirs}")
        
        # Se encontramos diretórios correspondentes, buscamos imagens dentro deles
        if matching_dirs:
            for dir_name in matching_dirs:
                dir_path = os.path.join(cell_dir, dir_name)
                images = []
                
                if os.path.isdir(dir_path):
                    # Listar todos os arquivos no diretório
                    dir_files = os.listdir(dir_path)
                    logging.debug(f"Arquivos no diretório {dir_name}: {dir_files}")
                    
                    for filename in dir_files:
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            # Criar URL completa para a imagem
                            image_url = url_for('get_photo', cell_name=cell_name, filepath=f"{dir_name}/{filename}")
                            images.append(image_url)
                    
                    # Se encontramos imagens, retornamos
                    if images:
                        # Ordenar imagens pelo nome (normalmente image_1.jpg, image_2.jpg, etc)
                        images.sort()
                        logging.debug(f"Imagens encontradas: {images}")
                        return jsonify({
                            "success": True,
                            "images": images
                        })
        
        # Se não encontramos em diretórios dedicados, procuramos por arquivos diretos
        # com o mesmo padrão de nome
        direct_images = []
        for file in all_files:
            file_path = os.path.join(cell_dir, file)
            # Verificar se é um arquivo de imagem e se contém o nome da ordem
            if os.path.isfile(file_path) and file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if order_number in file:
                    image_url = url_for('get_photo', cell_name=cell_name, filepath=file)
                    direct_images.append(image_url)
        
        if direct_images:
            logging.debug(f"Imagens diretas encontradas: {direct_images}")
            return jsonify({
                "success": True,
                "images": direct_images
            })
        
        # Se não encontramos imagens em nenhum lugar
        logging.warning(f"Nenhuma imagem encontrada para o setup: {order_number}_{setup_type}")
        return jsonify({
            "success": False,
            "images": []
        })
    except Exception as e:
        logging.error(f"Erro ao buscar imagens: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "images": [],
            "error": str(e)
        })

def reset_cell_flow(cell_name, reason):
    """Reset the flow of a cell without deleting records.
    
    Args:
        cell_name: Nome da célula para resetar o fluxo
        reason: Motivo para o reset do fluxo
    
    Returns:
        bool: True se o reset foi bem-sucedido, False caso contrário
        str: Mensagem de status
    """
    if not cell_name or not reason:
        return False, "Célula e motivo são obrigatórios"
    
    try:
        # Criar timestamp para registro
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        cell_dir = os.path.join(DATA_DIR, cell_name)
        ensure_dir(cell_dir)
        
        # Criar diretório de resets se não existir
        resets_dir = os.path.join(cell_dir, "resets")
        ensure_dir(resets_dir)
        
        # Registrar informações do reset
        username = session.get("username", "Unknown")
        reset_filename = f"{'auto' if reason.startswith('auto:') else 'manual'}_reset_{timestamp}.json"
        reset_file_path = os.path.join(resets_dir, reset_filename)
        
        # Preparar dados para o log de reset
        reset_data = {
            "cell_name": cell_name,
            "reset_timestamp": timestamp.replace('_', ' '),
            "reset_reason": reason,
            "reset_by": username,
            "previous_state": {
                "had_removal": False, 
                "had_supply": False
            }
        }
        
        # Verificar estado atual antes de resetar
        cell_files = []
        if os.path.isdir(cell_dir):
            for file in os.listdir(cell_dir):
                # Encontrar os arquivos de setup (não os de reset)
                if file.endswith(".txt") and not file.startswith("reset_log_"):
                    file_path = os.path.join(cell_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            setup_data = json.load(f)
                        
                        setup_type = setup_data.get('setup_type')
                        if setup_type == 'removal':
                            reset_data["previous_state"]["had_removal"] = True
                        elif setup_type == 'supply':
                            reset_data["previous_state"]["had_supply"] = True
                    except Exception as e:
                        logging.error(f"Erro ao ler arquivo durante reset: {file_path}: {e}")
        
        # Registrar o reset
        with open(reset_file_path, 'w') as f:
            json.dump(reset_data, f)
        
        # Atualizar o histórico de resets
        history_file = os.path.join(resets_dir, "reset_history.json")
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                logging.error(f"Erro ao carregar histórico de resets: {e}")
        
        # Adicionar este reset ao histórico
        history.append({
            "timestamp": timestamp.replace('_', ' '),
            "reason": reason,
            "user": username,
            "file": reset_filename
        })
        
        # Salvar histórico atualizado
        with open(history_file, 'w') as f:
            json.dump(history, f)
        
        return True, "Fluxo da célula resetado com sucesso"
    except Exception as e:
        logging.error(f"Erro ao resetar o fluxo da célula: {e}")
        return False, f"Erro ao resetar célula: {str(e)}"
        
@app.route("/api/reset_cell", methods=["POST"])
def api_reset_cell():
    """API endpoint to reset the flow of a cell."""
    # Verificar se o usuário está logado
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem perfil de auditor
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Somente auditores podem resetar o fluxo da célula"}), 403
    
    # Aceitar dados tanto via JSON quanto via FormData
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    # Log para debug
    logging.debug(f"API reset_cell: Recebido dados: {data}")
    
    cell_name = data.get('cell_name')
    reset_reason = data.get('reset_reason')
    
    if not cell_name or not reset_reason:
        return jsonify({"success": False, "message": "Célula e motivo são obrigatórios"}), 400
    
    success, message = reset_cell_flow(cell_name, reset_reason)
    
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route('/camera_test')
def camera_test():
    """Página de teste para verificar o acesso à câmera."""
    return render_template('camera_test.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# Rota para a página de gerenciamento de produtos
@app.route('/product_management')
def product_management():
    """Página de gerenciamento de produtos e itens para as células."""
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        flash('Acesso restrito. Apenas auditores podem acessar esta página.', 'danger')
        return redirect(url_for('index'))
    
    # Obter todas as células cadastradas
    cells = get_all_cells()
    
    return render_template('product_management.html', cells=cells)

# API para adicionar produto a uma célula
@app.route('/api/add_product', methods=['POST'])
def api_add_product():
    """API para adicionar um produto a uma célula."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito."}), 403
    
    # Obter dados da requisição
    data = request.json
    cell_name = data.get('cell_name')
    product_code = data.get('product_code')
    product_name = data.get('product_name')
    
    if not all([cell_name, product_code, product_name]):
        return jsonify({"success": False, "message": "Todos os campos são obrigatórios"}), 400
    
    # Adicionar produto à célula
    success = add_product_to_cell(cell_name, product_code, product_name)
    
    if success:
        return jsonify({"success": True, "message": "Produto adicionado com sucesso"})
    
    return jsonify({"success": False, "message": "Erro ao adicionar produto. Célula não encontrada."}), 404

# API para adicionar item a um produto
@app.route('/api/add_item', methods=['POST'])
def api_add_item():
    """API para adicionar um item a um produto."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito."}), 403
    
    # Obter dados da requisição
    data = request.json
    cell_name = data.get('cell_name')
    product_code = data.get('product_code')
    item_code = data.get('item_code')
    item_name = data.get('item_name')
    
    if not all([cell_name, product_code, item_code, item_name]):
        return jsonify({"success": False, "message": "Todos os campos são obrigatórios"}), 400
    
    # Adicionar item ao produto
    success = add_item_to_product(cell_name, product_code, item_code, item_name)
    
    if success:
        return jsonify({"success": True, "message": "Item adicionado com sucesso"})
    
    return jsonify({"success": False, "message": "Erro ao adicionar item. Célula ou produto não encontrado."}), 404

# API para obter produtos de uma célula
@app.route('/api/cell_products/<cell_name>')
def api_cell_products(cell_name):
    """API para obter produtos de uma célula."""
    # Permitir acesso até mesmo sem autenticação para facilitar o fluxo
    # Isso é necessário para o funcionamento do script de carregamento de produtos
    
    logging.info(f"API cell_products: Buscando produtos para célula={cell_name}")
    
    if not cell_name:
        logging.error("API cell_products: Nome da célula está vazio")
        return jsonify({
            "success": False, 
            "message": "Nome da célula não fornecido", 
            "products": []
        })
    
    # Obter produtos da célula
    try:
        products = get_cell_products(cell_name)
        product_count = len(products)
        
        logging.info(f"API cell_products: {product_count} produtos encontrados para célula {cell_name}")
        
        # Log detalhado dos produtos (até 5 produtos para não sobrecarregar os logs)
        if product_count > 0:
            preview = products[:5]
            logging.debug(f"API cell_products: Primeiros produtos encontrados: {json.dumps(preview, indent=2)}")
        
        return jsonify({
            "success": True, 
            "products": products,
            "count": product_count,
            "message": f"{product_count} produtos encontrados para célula {cell_name}"
        })
    except Exception as e:
        logging.error(f"API cell_products: Erro ao buscar produtos: {str(e)}")
        return jsonify({
            "success": False, 
            "message": f"Erro ao buscar produtos: {str(e)}", 
            "products": []
        })

# API para obter itens de um produto
@app.route('/api/product_items/<cell_name>/<product_code>')
def api_product_items(cell_name, product_code):
    """API para obter itens de um produto."""
    # Permitir acesso até mesmo sem autenticação para facilitar o fluxo
    # Isso é necessário para o funcionamento do script de carregamento de produtos
    
    logging.info(f"API product_items: Buscando itens para célula={cell_name}, produto={product_code}")
    
    if not cell_name or not product_code:
        logging.error("API product_items: Nome da célula ou código do produto está vazio")
        return jsonify({
            "success": False, 
            "message": "Nome da célula e código do produto são obrigatórios", 
            "items": []
        })
    
    # Obter itens do produto
    try:
        items = get_product_items(cell_name, product_code)
        item_count = len(items)
        
        logging.info(f"API product_items: {item_count} itens encontrados para produto {product_code} na célula {cell_name}")
        
        # Log detalhado dos itens (até 5 itens para não sobrecarregar os logs)
        if item_count > 0:
            preview = items[:5]
            logging.debug(f"API product_items: Primeiros itens encontrados: {json.dumps(preview, indent=2)}")
        
        return jsonify({
            "success": True, 
            "items": items,
            "count": item_count,
            "message": f"{item_count} itens encontrados para produto {product_code}"
        })
    except Exception as e:
        logging.error(f"API product_items: Erro ao buscar itens: {str(e)}")
        return jsonify({
            "success": False, 
            "message": f"Erro ao buscar itens: {str(e)}", 
            "items": []
        })

# API para excluir um produto
@app.route('/api/delete_product', methods=['POST'])
def api_delete_product():
    """API para excluir um produto."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito."}), 403
    
    # Obter dados da requisição
    data = request.json
    cell_name = data.get('cell_name')
    product_code = data.get('product_code')
    
    if not all([cell_name, product_code]):
        return jsonify({"success": False, "message": "Célula e código do produto são obrigatórios"}), 400
    
    # Remover produto da célula
    success = remove_product_from_cell(cell_name, product_code)
    
    if success:
        return jsonify({"success": True, "message": "Produto excluído com sucesso"})
    
    return jsonify({"success": False, "message": "Erro ao excluir produto. Célula não encontrada."}), 404

# API para excluir um item
@app.route('/api/delete_item', methods=['POST'])
def api_delete_item():
    """API para excluir um item de um produto."""
    if not session.get('logged_in'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Verificar se o usuário tem permissão (apenas auditores)
    username = session.get('username')
    users = get_users()
    user_profile = users.get(username, {}).get('profile', 'supplier')
    
    if user_profile != 'auditor':
        return jsonify({"success": False, "message": "Acesso restrito."}), 403
    
    # Obter dados da requisição
    data = request.json
    cell_name = data.get('cell_name')
    product_code = data.get('product_code')
    item_code = data.get('item_code')
    
    if not all([cell_name, product_code, item_code]):
        return jsonify({"success": False, "message": "Célula, código do produto e código do item são obrigatórios"}), 400
    
    # Remover item do produto
    success = remove_item_from_product(cell_name, product_code, item_code)
    
    if success:
        return jsonify({"success": True, "message": "Item excluído com sucesso"})
    
    return jsonify({"success": False, "message": "Erro ao excluir item. Célula ou produto não encontrado."}), 404

# Chamar a função de atualização do formato de QR codes ao iniciar
with app.app_context():
    update_qrcodes_format()
