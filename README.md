# Blog Automation and Publishing Script

This script automates the generation of blog post content, images, and publishing workflows using OpenAI, GetIMG, Django API, and Pinterest. It:

- Generates SEO-optimized blog titles, keywords, and descriptions via OpenAI GPT-4O-mini.
- Produces detailed ideas and descriptions for each blog post section.
- Generates hyper-realistic images for each idea using GetIMG.ai and converts them to WebP.
- Uploads assets to a remote server over SSH (Paramiko).
- Publishes posts to a Django backend via REST API, including featured images and metadata.
- Automates Pinterest pin creation with Selenium WebDriver, logging in, uploading images, and selecting/creating boards.

---

## Features

- **Title Generation**: Craft catchy numbered list titles under 100 characters.
- **Keyword Generation**: Produce 6 SEO-friendly Pinterest hashtags.
- **Main Description**: Create an engaging 155-character intro for meta-description.
- **Idea Expansion**: Generate and parse 45+ word descriptive ideas.
- **Image Generation**: Create and convert images to WebP for each idea.
- **Server Upload**: Securely transfer media via SSH/SFTP.
- **Django Publishing**: Send post data and images to a Django REST endpoint.
- **Pinterest Automation**: Log in, publish pins to themed boards with Selenium.
- **Configurable**: Easily adjust `theme` and number of executions (`x`) in `main()`.

---

## Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- ChromeDriver executable in your `$PATH`
- A running Django API endpoint for posts and themes

### Python Dependencies

Install via pip:

```bash
pip install -r requirements.txt
```

`requirements.txt` should include:

```
openai
requests
paramiko
Pillow
selenium
python-dotenv
django
```

---

## Environment Variables

Create a `.env` file in the project root with the following:

```ini
OPENAI_KEY=your_openai_api_key
GETIMG_KEY=your_getimg_api_key
PINTEREST_EMAIL=your_pinterest_email
PINTEREST_PASSWORD=your_pinterest_password
DJANGO_API_TOKEN=your_django_api_token
```

- **OPENAI_KEY**: API key for OpenAI GPT calls.
- **GETIMG_KEY**: API key for GetIMG.ai image generation.
- **PINTEREST_EMAIL / _PASSWORD_**: Credentials for Pinterest automation.
- **DJANGO_API_TOKEN**: Token for authenticating with the Django REST API.

---

## Configuration

- Adjust the default `theme` and number of runs `x` in the `if __name__ == "__main__"` block.
- Ensure `server`, `username`, and `password` in `upload_to_server()` match your remote host.
- Confirm Django REST endpoints (`/api/api_posts/` and `/api/themes/`) are accessible.

---

## Usage

Run the script from the command line:

```bash
python script.py
```

The script will:
1. Log in to Pinterest.
2. For each execution:
   - Generate a blog title.
   - Produce related ideas and descriptions.
   - Generate and upload images.
   - Publish the post to Django.
   - Create a Pinterest pin with the featured image and metadata.
3. Close the WebDriver when done.

---

## How It Works

1. **Title & Content Generation**: Functions in `generate_blog_title()`, `generate_keywords()`, and `generate_main_description()` handle GPT prompts and response parsing.
2. **Idea Expansion**: `generate_related_ideas()` loops to request each idea and uses regex to parse structured responses.
3. **Image Handling**: `generate_image()` calls GetIMG, downloads images, and `convert_to_webp()` compresses to WebP.
4. **Server Upload**: `upload_to_server()` uses Paramiko SSH/SFTP to transfer media files.
5. **Django API**: `publish_to_django()` sends post metadata, content, and featured image to the Django backend.
6. **Pinterest Automation**: Selenium-based functions (`login_pinterest()`, `publish_on_pinterest()`) open Chrome, log in, and publish pins.

---

## Function Reference

- `generate_blog_title(theme)`
- `generate_keywords(title, theme)`
- `generate_main_description(theme, title)`
- `generate_related_ideas(title)`
- `generate_image(prompt)`
- `convert_to_webp(image, path)`
- `upload_to_server(local_path, remote_path, server, username, password)`
- `publish_to_django(...)`
- `login_pinterest(driver, wait, email, password)`
- `publish_on_pinterest(driver, wait, title, description, image_path, url, theme)`
- `publish_and_generate_blog(title, theme, driver, wait)`
- `main(theme, x)`

---

## Customization

- Modify prompts in the GPT functions to suit your brand voice.
- Adjust image generation parameters (`width`, `height`, `steps`, `quality`).
- Enhance error handling or logging as needed.

---

## Contributing

1. Fork the repository.
2. Create a new branch: `git checkout -b feature/add-something`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature/add-something`
5. Submit a Pull Request.

---

## 📝 License

MIT License

---

## ✉️ Contact

Levi Lael • [linkedin.com/in/levilael](https://www.linkedin.com/in/levi-lael-939b4a1b9/)