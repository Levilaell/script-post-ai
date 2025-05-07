import io
import json
import os
import random
import re
import time
import traceback
from pathlib import Path
import openai
import paramiko
import requests
from django.utils.text import slugify
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

load_dotenv()

# Configurações de API
openai.api_key = os.getenv('OPENAI_KEY')
GETIMG_API_KEY = os.getenv('GETIMG_KEY')
pinterest_email = os.getenv('PINTEREST_EMAIL')
pinterest_password = os.getenv('PINTEREST_PASSWORD')

# ========================
# Generate Blog Texts
# ========================

def generate_blog_title(theme, attempt=1, max_attempts=2):

    number_of_ideas = random.choice([3, 4, 5, 6, 7])

    prompt = (
        f"Given the theme '{theme}', generate a catchy blog title that starts with the number {number_of_ideas}, following the style of the examples below. "
        f"Ensure the title is no longer than 100 characters, including spaces and punctuation:\n\n"
        f"{number_of_ideas} Ways to Elevate Your Home Office Design for Maximum Comfort (You Won't Believe #1!)\n"
        f"{number_of_ideas} Nail Art Trends You'll Want to Try This Season (Holiday Magic Alert at #2!)\n"
        f"{number_of_ideas} Hidden Gems in Europe Every Traveler Should Visit (Hint: #3 Is Revolutionary!)\n"
        f"Please generate one blog title in this format for the theme '{theme}', starting with the number {number_of_ideas}."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        title = response.choices[0].message['content'].strip()

        if len(title) > 100:
            if attempt < max_attempts:
                print(f"O título gerado excede 100 caracteres. Tentativa {attempt} de {max_attempts}...")
                return generate_blog_title(theme, attempt + 1)
            else:
                return title

        print(title)
        return title
    
    except Exception as e:
        print("Erro ao gerar título:", e)
        return None

def generate_keywords(title, theme):
    """Gera palavras-chave relevantes com base no título e tema usando o GPT."""
    prompt = (
        f"Based on the blog title '{title}' and the theme '{theme}', generate 6 SEO-friendly keywords. "
        "These keywords should target Pinterest users looking for ideas or inspiration in this niche. "
        "Return the keywords separated by commas."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        keywords = response.choices[0].message['content'].strip()
        # Separar as palavras-chave geradas e formatar como hashtags
        hashtags = ', '.join([f"#{slugify(keyword.strip())}" for keyword in keywords.split(",")])
        print("Keywords geradas:", hashtags)
        return hashtags
    except Exception as e:
        print("Erro ao gerar palavras-chave:", e)
        return ""


def generate_main_description(theme, title):
    """Gera uma descrição principal para o post do blog usando a API do OpenAI, limitada a 155 caracteres."""
    prompt = (
        f"Generate a brief introductory description for a blog post titled '{title}' about '{theme}'. "
        "This description should engage the reader and provide context for the ideas that follow. "
        "Aim for 2-3 sentences and ensure the total length does not exceed 155 characters."
    )
    try:
        print("Gerando main_description")
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        description = response.choices[0].message['content'].strip()
        # Assegura que a descrição não exceda 155 caracteres
        if len(description) > 155:
            print(f"main_description excede 155 caracteres ({len(description)}). Truncando...")
            description = description[:152].rstrip() + "..."
        print("Descrição gerada:", description)     
        return description
    except Exception as e:
        print("Erro ao gerar a descrição principal:", e)
        return ""

def extract_number_from_title(title):
    """Extrai o primeiro número encontrado no título ou retorna 5 se não encontrar."""
    match = re.search(r'\d+', title)
    return int(match.group()) if match else 5


def parse_idea_response(text):
    """Analisa o texto de resposta e extrai a ideia e a descrição."""
    pattern = re.compile(r'Idea:\s*(.+?)\nDescription:\s*(.+)', re.DOTALL)
    match = pattern.search(text)

    if match:
        idea = match.group(1).strip()
        description = match.group(2).strip()
        if idea and description and len(description.split()) >= 45:
            return {
                'idea': idea,
                'description': description
            }
    return None




def generate_related_ideas(title):
    """Gera ideias relacionadas fazendo requisições individuais para cada ideia."""
    num_ideas = extract_number_from_title(title)
    ideas_with_descriptions = []
    max_attempts_per_idea = 3  # Número de tentativas por ideia

    for i in range(1, num_ideas + 1):
        attempt = 0
        while attempt < max_attempts_per_idea:
            attempt += 1
            print(f"Generating idea {i} of {num_ideas}, attempt {attempt} of {max_attempts_per_idea}...")

            prompt = (
                f"Based on the blog title '{title}', generate idea number {i} out of {num_ideas}. "
                "The idea should include a catchy phrase and a detailed description of at least 45 words. "
                "Format:\nIdea: [Catchy Phrase]\nDescription: [Description]"
                "Do not include any additional text or formatting outside this format."
            )

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                idea_text = response.choices[0].message['content'].strip()
                # Analisar a ideia e a descrição da resposta
                idea_data = parse_idea_response(idea_text)
                if idea_data:
                    ideas_with_descriptions.append(idea_data)
                    break  # Sai do loop de tentativas para esta ideia
                else:
                    print(f"Error: Could not parse idea {i}. Retrying...")
            except Exception as e:
                print(f"Error generating idea {i}:", e)
        else:
            print(f"Failed to generate idea {i} after {max_attempts_per_idea} attempts.")
            # Você pode decidir continuar ou sair, dependendo da sua preferência

    return ideas_with_descriptions


def clean_response_text(text, num_ideas):
    """Limpa o texto de resposta do OpenAI e extrai ideias com descrições."""
    pattern = re.compile(r'Idea:\s*(.+?)\nDescription:\s*(.+?)(?=\nIdea:|\Z)', re.DOTALL)
    matches = pattern.findall(text)
    
    cleaned_ideas = []
    for match in matches:
        idea = match[0].strip()
        description = match[1].strip()
        if idea and description and len(description.split()) >= 45:
            cleaned_ideas.append({
                'idea': idea,
                'description': description
            })
    
    return cleaned_ideas

# ========================
# Generate Blog Images
# ========================

def convert_to_webp(image, output_path, quality=80):
    """
    Converte a imagem para o formato WebP com compressão.

    :param image: Objeto PIL Image
    :param output_path: Caminho para salvar a imagem WebP
    :param quality: Qualidade de compressão (0-100), maior é melhor qualidade
    """
    # Converte a imagem para RGB se necessário
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    # Salva a imagem em formato WebP com a qualidade especificada
    image.save(output_path, format='WEBP', quality=quality, method=6)


def generate_image_prompt(title, idea, description):
    '''
    print(f"Create a high-quality image inspired by {title}, the idea '{idea}' and the description: '{description}'. Realistic image. Vibrant colors. No text.")
    """Gera o prompt para a geração de imagens com base na ideia e descrição."""
    return f"Create a high-quality image inspired by {title}, the idea '{idea}' and the description: '{description}'. Realistic image. Vibrant colors. No text."
    '''

    prompt = (
        f"Generate a hyper-realistic image based on the title: '{title}'. "
        f"Visually represent the idea: '{idea}' by accurately reflecting the details provided: '{description}'. "
        "Ensure the scene is richly detailed with realistic textures, natural lighting, and a dynamic composition that emphasizes depth and perspective. "
        "Incorporate vivid, lifelike colors and pay close attention to small details that enhance the realism and immersion of the image. "
        "Avoid including text, watermarks, or elements not explicitly described, and prioritize a clean, polished presentation."
    )

    print(prompt)
    return prompt

def generate_image(prompt):
    url = "https://api.getimg.ai/v1/flux-schnell/text-to-image"

    payload = {
        "prompt": prompt,
        "width": 768,
        "height": 1280,
        "steps": 4,
        "output_format": "jpeg",
        "response_format": "url"
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {GETIMG_API_KEY}"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_json = response.json()
        print(f"Response JSON: {response_json}")  # Debugging line
        image_url = response_json.get('url')
        if image_url:
            # Download the image
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                img = Image.open(io.BytesIO(image_response.content))
                return img
            else:
                print(f"Error downloading image: {image_response.status_code}")
                return None
        else:
            print("No image URL returned in response.")
            return None
    else:
        print(f"Error generating image: {response.status_code} {response.text}")
        return None


# ========================
# Generate Blog Content
# ========================

def upload_to_server(local_path, remote_path, server, username, password):
    """Faz upload do arquivo local para o servidor remoto via SSH."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Conectando ao servidor: {server} como usuário: {username}")
    
    try:
        # Conecta ao servidor
        ssh.connect(server, username=username, password=password)

        # Inicia SFTP para transferência de arquivos
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        # print(f"Arquivo enviado: {local_path} -> {remote_path}")

        sftp.close()
        ssh.close()
    except Exception as e:
        print(f"Erro ao conectar ou transferir arquivo: {e}")



def generate_blog_content(title, ideas_with_descriptions, theme):
    # Caminhos locais
    local_media_root = Path.home() / "media"
    images_dir = local_media_root / "images"
    featured_images_dir = local_media_root / "featured_images"

    # Criar diretórios locais
    images_dir.mkdir(parents=True, exist_ok=True)
    featured_images_dir.mkdir(parents=True, exist_ok=True)

    # Caminhos remotos
    remote_media_root = "/srv/media"
    remote_images_dir = f"{remote_media_root}/images"
    remote_featured_images_dir = f"{remote_media_root}/featured_images"

    # Inicializar conteúdo
    content = {
        "meta_description": "",
        "main_description": "",
        "ideas": []
    }
    featured_image_local_path = None
    featured_image_remote_path = None

    # Gerar main_description (limitada a 155 caracteres)
    main_description = generate_main_description(theme, title)
    content["main_description"] = main_description

    # Usar main_description como meta_description
    content["meta_description"] = main_description

    for i, item in enumerate(ideas_with_descriptions, 1):
        idea = item['idea']
        description = item['description']
        image_prompt = generate_image_prompt(title, idea, description)
        image = generate_image(image_prompt)

        if image:
            local_image_filename = f"{sanitize_filename(title)}_{i}.webp"
            local_image_path = (featured_images_dir if i == 1 else images_dir) / local_image_filename
            convert_to_webp(image, local_image_path)


            # Caminho remoto
            remote_image_path = (
                f"{remote_featured_images_dir}/{local_image_filename}"
                if i == 1 else
                f"{remote_images_dir}/{local_image_filename}"
            )

            # Upload para o servidor
            upload_to_server(
                local_path=str(local_image_path),
                remote_path=remote_image_path,
                server="srv643463.hstgr.cloud",  # Ou "217.21.78.21"
                username="root",
                password=":6S39:g==Mb[w6l2Ua9Y"
            )

            content["ideas"].append({
                "title": f"{i}. {idea}",
                "description": description,
                "image_url": f"/media/featured_images/{local_image_filename}" if i == 1 else f"/media/images/{local_image_filename}"
            })


            if i == 1:
                featured_image_local_path = str(local_image_path)  # Caminho local da imagem destacada
                featured_image_remote_path = remote_image_path     # Caminho remoto da imagem destacada

    return content, featured_image_local_path, featured_image_remote_path


# ========================
# Publish to Django
# ========================

def sanitize_filename(filename, max_length=93):
    """
    Sanitiza o nome do arquivo removendo caracteres especiais e truncando se necessário.
    """
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[^\w\-_.]', '', filename)  # Remove caracteres não permitidos
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip("_")
    return filename
import json


# script-django.py
def publish_to_django(title, content, main_description, meta_description, ideas, featured_image_path=None, theme_slug=None, token_autenticacao=None):
    url = 'https://www.dailydecorideas.com/api/api_posts/'
    headers = {
        'Authorization': f'Token {token_autenticacao}' if token_autenticacao else '',
    }

    slug = slugify(title)[:50]

    # Prepare data
    data = {
        'title': title,
        'content': content,  # Conteúdo principal do post (limitado a 155 caracteres)
        'main_description': main_description,
        'meta_description': meta_description,  # Também limitado a 155 caracteres
        'ideas': json.dumps(ideas),
    }

    # Para temas, garantir que seja uma lista de slugs
    if theme_slug:
        data['themes'] = theme_slug if isinstance(theme_slug, list) else [theme_slug]

    # Prepare files dictionary
    files = {}
    if featured_image_path and os.path.exists(featured_image_path):
        files['featured_image'] = open(featured_image_path, 'rb')
    else:
        print(f"Erro: O caminho da imagem destacada '{featured_image_path}' não existe ou não é acessível.")

    # print("Data being sent to the server:")
    # print(json.dumps(data, indent=2))  # Pretty-print JSON data
    # print("Files being sent to the server:")
    # print(files)

    # Enviar a requisição POST
    response = requests.post(url, headers=headers, data=data, files=files)

    # Fechar o arquivo após a requisição
    if 'featured_image' in files:
        files['featured_image'].close()

    if response.status_code == 201:
        print('Postagem e ideias criadas com sucesso!')
    else:
        print(f'Erro ao criar postagem: {response.status_code}')
        print(f'Resposta do servidor: {response.text}')
    return response

# ========================
# Publish on Pinterest
# ========================

def initialize_webdriver():
    """Inicializa o WebDriver do Selenium com opções personalizadas."""
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    # Opcional: Executar em modo headless (sem interface gráfica)
    # options.add_argument('--headless')
    # Desativar logs desnecessários
    options.add_argument('--log-level=3')
    # Desativar funcionalidades USB para evitar erros
    options.add_argument("--disable-usb")
    options.add_argument("--disable-webusb")
    options.add_argument("--disable-extensions")  # Opcional: desativa extensões que possam interagir com USB

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)  # Aumentado para 30 segundos para conexões mais lentas
    return driver, wait

def login_pinterest(driver, wait, email, password):
    """Faz login no Pinterest usando o WebDriver."""
    try:
        print('Abrindo Pinterest para login...')
        driver.get("https://www.pinterest.com/login/")
        
        # Espera o campo de email
        email_input = wait.until(EC.visibility_of_element_located((By.NAME, "id")))
        email_input.send_keys(email)

        # Espera o campo de senha
        password_input = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        print('Logado com sucesso')
        
        # Espera a página inicial após o login
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='dynamic-menu-controller']")))
        print('Página inicial carregada após login.')

    except Exception as e:
        print("Erro durante o login:", e)
        driver.save_screenshot("login_error.png")
        driver.quit()
        raise e

def verify_and_truncate_title(titulo, limite=100):
    """Verifica se o título excede o limite e o trunca se necessário."""
    print(f"Verificando título com {len(titulo)} caracteres.")
    if len(titulo) > limite:
        print(f"Título excede {limite} caracteres. Truncando...")
        # Trunca para (limite - 3) para adicionar '...' sem exceder o limite
        titulo = titulo[:limite - 3].rstrip() + "..."
        print(f"Título truncado: {titulo} (Comprimento: {len(titulo)} caracteres)")
    else:
        print("Título está dentro do limite.")
    return titulo

def publish_on_pinterest(driver, wait, title, description, image_path, url, theme):
    """Publishes a pin on Pinterest, selecting the board that matches the theme."""
    if not image_path or not os.path.exists(image_path):
        print("No valid image path provided. Skipping Pinterest publishing.")
        return
    
    keywords = generate_keywords(title, theme)

    # Atualizar a descrição com as palavras-chave
    new_description = (
        description + 
        " Save these ideas now and make your dream living room a reality! " + 
        keywords
    )

    
    try:
        print('Preparing to publish on Pinterest...')
        
        # Convert image path to absolute
        image_path = os.path.abspath(image_path)
        
        # Click on the "Create" menu/button
        try:
            create_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@data-test-id='dynamic-menu-controller']/parent::div[@role='button']")
            ))     
            create_button.click()
            print('Create menu opened')
            random_sleep(2, 4)
        except Exception as e:
            print("Error locating 'Create' button:", e)
            driver.save_screenshot("create_button_error.png")
            return

        # Click on "Create Pin" option
        try:
            create_pin_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/pin-builder/']")))
            create_pin_button.click()
            print('Clicked Create Pin')
            random_sleep(2, 4)
        except Exception as e:
            print("Error locating 'Create Pin' button:", e)
            driver.save_screenshot("create_pin_button_error.png")
            return

        # Upload the image
        try:
            print('Uploading image...')
            image_upload_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            image_upload_input.send_keys(image_path)
            print('Image uploaded')
            random_sleep(2, 4)
        except Exception as e:
            print("Error uploading image:", e)
            driver.save_screenshot("image_upload_error.png")
            return

        # Insert title, description, and URL
        try:
            print('Inserting title...')
            title = verify_and_truncate_title(title)  
            title_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//textarea[@placeholder='Add your title']")))
            title_input.send_keys(title)
            print('Title inserted')
            random_sleep(1, 3)

            print('Inserting description...')
            description_input = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[starts-with(@data-test-id, 'pin-draft-description')]//div[@role='combobox']")
                )
            )
            actions = ActionChains(driver)
            actions.move_to_element(description_input).click().send_keys(new_description).perform()
            print('Description inserted')
            random_sleep(1, 3)

            print('Inserting link...')
            try:
                link_input = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//div[@data-test-id='pin-draft-link']//textarea[@placeholder='Add a destination link']")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", link_input)
                random_sleep(0.5, 1)
                actions = ActionChains(driver)
                actions.move_to_element(link_input).click().send_keys(url).perform()
                print('Link inserted')
            except Exception as e:
                print("Error inserting link:", e)
                driver.save_screenshot("insert_link_error.png")
                return

            random_sleep(1, 3)

        except Exception as e:
            print("Error inserting pin details:", e)
            driver.save_screenshot("insert_details_error.png")
            return

        # Select the board matching the theme
        try:
            print('Selecting board...')
            # Click on the board dropdown
            board_dropdown_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@data-test-id='board-dropdown-select-button']")
            ))
            board_dropdown_button.click()
            random_sleep(1, 2)

            # Search for the board by theme name
            search_input = wait.until(EC.visibility_of_element_located(
                (By.XPATH, "//input[contains(@placeholder, 'Search')]")
            ))
            search_input.send_keys(theme)
            random_sleep(1, 2)

            # Normalize theme
            theme_normalized = theme.strip().lower()

            # Wait for the board to appear in the list and select it
            board_xpath = (
                f"//div[@data-test-id='boardWithoutSection']//div[@role='button' and "
                f"descendant::div[normalize-space(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='{theme_normalized}']]"
            )
            from selenium.common.exceptions import (NoSuchElementException,
                                                    TimeoutException)
            try:
                board_option = wait.until(EC.element_to_be_clickable((By.XPATH, board_xpath)))
                board_option.click()
                print(f"Board '{theme}' selected")
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Board '{theme}' not found. Creating new board... Error: {e}")
                create_board_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[@data-test-id='create-board']"))
                )
                create_board_button.click()
                random_sleep(1, 2)

                # Enter the board name in the creation modal
                board_name_input = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "//input[@id='boardEditName']"))
                )
                board_name_input.clear()
                # board_name_input.send_keys(theme)
                random_sleep(1, 2)

                # Save the new board
                create_board_confirm_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[@data-test-id='board-form-submit-button']"))
                )
                create_board_confirm_button.click()
                print(f"Board '{theme}' created and selected")
                random_sleep(2, 3)

            random_sleep(1, 2)

        except Exception as e:
            print("Error selecting board:", e)
            traceback.print_exc()
            driver.save_screenshot("select_board_error.png")
            return

        # Publish the Pin
        try:
            print('Publishing...')
            publish_button = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//button[@data-test-id='board-dropdown-save-button' and .//div[text()='Publish']]"
            )))
            driver.execute_script("arguments[0].scrollIntoView(true);", publish_button)
            time.sleep(random.uniform(1, 2))
            actions = ActionChains(driver)
            actions.move_to_element(publish_button).click().perform()
            print('Clicked Publish button')
            # driver.save_screenshot("after_publish_click.png")
            random_sleep(7, 8)

            try:
                print('Pin published successfully!')
                modal_dismiss_button = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[@aria-label='dismiss']")
                ))
                modal_dismiss_button.click()
                print('Confirmation modal closed.')
                random_sleep(1, 2)

            except TimeoutException:
                print('Pin published (could not find a specific success message).')
                driver.save_screenshot("publish_no_success_message.png")

        except Exception as e:
            print("Error publishing the pin:", e)
            driver.save_screenshot("publish_error.png")
            return

    except Exception as e:
        print("Unexpected error during publishing on Pinterest:", e)
        traceback.print_exc()
        driver.save_screenshot("unexpected_error_publish.png")

# ========================
# Function to Publish Both
# ========================

def publish_and_generate_blog(title, theme, driver, wait):
    ideas_with_descriptions = generate_related_ideas(title)
    if not ideas_with_descriptions:
        print("Nenhuma ideia foi gerada.")
        return None  # Retorna None se não houver ideias

    # Token de autenticação seguro
    token = '1fbca8225f25f61a50abf42fb7a14518b25587ac'
    if not token:
        print("Token de autenticação não encontrado. Defina a variável de ambiente 'DJANGO_API_TOKEN'.")
        return None

    # Garantir que o tema exista e obter seu slug
    theme_slug = slugify(theme)
    ensure_theme_exists(theme, token)

    # Gerar o conteúdo do blog e a imagem destacada
    content_data, featured_image_local_path, featured_image_remote_path = generate_blog_content(title, ideas_with_descriptions, theme)
    # print("Conteúdo gerado:", content_data)

    if not featured_image_local_path:
        print("Image generation failed. Skipping Pinterest publishing.")
        return {
            "title": title,
            "main_description": main_description,
            "featured_image_path": None,
            "post_url": post_url
        }

    # Extrair as informações do dicionário content_data
    main_description = content_data['main_description']
    meta_description = content_data['meta_description']
    ideas = content_data['ideas']

    # Chamar publish_to_django com os argumentos corretos
    post_response = publish_to_django(
        title=title,
        content=main_description,  # Conteúdo principal do post
        main_description=main_description,
        meta_description=meta_description,
        ideas=ideas,
        featured_image_path=featured_image_local_path,  # Use o caminho local aqui
        theme_slug=theme_slug,  # Passar o slug do tema
        token_autenticacao=token
    )

    post_url = None  # Inicializa post_url como None
    if post_response and post_response.status_code == 201:
        response_data = post_response.json()

        post_url = response_data.get("link")
        post_id = response_data.get("id")

        if post_url:
            print(f"Postagem criada com sucesso. URL: {post_url}")
        elif post_id:
            print(f"Postagem criada com sucesso. ID: {post_id}")
        else:
            print("A URL ou ID da postagem não foram encontrados na resposta da API.")
    else:
        print("Não foi possível publicar no Django ou obter o ID da imagem destacada.")
        return None  # Retorna None se a publicação falhar

    # Retorna os dados necessários para publicar no Pinterest
    return {
        "title": title,
        "main_description": main_description,
        "featured_image_path": featured_image_local_path,  # Use o caminho local aqui
        "post_url": post_url
    }




# ========================
# Helper Functions
# ========================

def random_sleep(min_seconds=2, max_seconds=5):
    """Faz uma pausa aleatória entre min_seconds e max_seconds para simular comportamento humano."""
    sleep_time = random.uniform(min_seconds, max_seconds)
    # print(f'Aguardando {sleep_time:.2f} segundos...')
    time.sleep(sleep_time)

def ensure_theme_exists(theme_name, token_autenticacao):
    url = 'https://www.dailydecorideas.com/api/themes/'
    headers = {
        'Authorization': f'Token {token_autenticacao}' if token_autenticacao else '',
    }

    theme_slug = slugify(theme_name)

    # Verificar se o tema já existe
    response = requests.get(f"{url}?slug={theme_slug}", headers=headers)
    # print(f"GET {response.url} -> {response.status_code}")
    if response.status_code == 200:
        themes = response.json()
        # print("Themes data:", themes)
        if themes:
            # Verificar se o tema com o slug específico existe
            for theme in themes:
                if theme['slug'] == theme_slug:
                    print(f"Tema '{theme_name}' já existe.")
                    return theme_slug
            print(f"Tema '{theme_name}' não encontrado na resposta.")
        else:
            print(f"Nenhum tema encontrado com o slug '{theme_slug}'.")
    else:
        print(f"Erro ao verificar existência do tema: {response.status_code}")

    # Se não existir, criar o tema
    data = {
        'name': theme_name,
    }
    response = requests.post(url, headers=headers, json=data)
    # print(f"POST {url} -> {response.status_code}")
    if response.status_code == 201:
        print(f"Tema '{theme_name}' criado com sucesso.")
        return theme_slug
    else:
        print(f"Erro ao criar tema: {response.status_code}")
        return None


# ========================
# Main Function
# ========================

def main(theme, x):
    """Main function that executes the process of generation and publishing."""
    driver, wait = initialize_webdriver()
    try:
        login_pinterest(driver, wait, pinterest_email, pinterest_password)
        
        for i in range(x):
            print(f"Execution {i+1} of {x}")
            blog_title = generate_blog_title(theme)
            if blog_title:
                result = publish_and_generate_blog(blog_title, theme, driver, wait)
                if result:
                    # Call publish_on_pinterest with the correct parameters
                    publish_on_pinterest(
                        driver=driver,
                        wait=wait,
                        title=result['title'],
                        description=result['main_description'],
                        image_path=result['featured_image_path'],
                        url=result['post_url'],
                        theme=theme  # Pass the theme here
                    )

                    # Small pause between executions to avoid detection
                    random_sleep(4, 5)
                else:
                    print("Failed to publish and generate blog.")
            else:
                print("Could not generate a title for the provided theme.")
                continue

    except Exception as e:
        print("General script error:", e)
        traceback.print_exc()
    finally:
        driver.quit()
        print("WebDriver closed.")

# ========================
# Script Exec
# ========================

if __name__ == "__main__":
    # theme_slugs = [christmas-decor-ideas', 'living-room-decor-ideas', 'interior-design-ideas', 'bathroom-decor-ideas']
    # change number of ideas in generate_blog_title()
    x = 24  # number of executions
    theme = "christmas decor ideas"

    main(theme, x)