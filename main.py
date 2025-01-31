import os
import asyncio
import logging
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.action_chains import ActionChains
from telegram.ext import ApplicationBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("karta_pobytu_scanner.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBPAGE_URL = "https://webqms.lublin.uw.gov.pl/"


async def send_telegram_message(token, chat_id, message):
    application = ApplicationBuilder().token(token).build()
    await application.bot.send_message(chat_id=chat_id, text=message)


def wait_for_dalej_button(driver):
    try:
        logger.info("Waiting for 'Dalej' button...")
        dalej_button_xpath = "//button[contains(@class, 'footer-btn') and contains(text(), 'Dalej')]"
        dalej_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, dalej_button_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView();", dalej_button)
        driver.execute_script("arguments[0].click();", dalej_button)
        logger.info("'Dalej' button clicked successfully.")
        return True
    except Exception as e:
        logger.error(f"Error clicking Dalej button: {e}")
        return False


def setup_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Set a Polish user-agent string
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 PL")

    service = Service()  # No need to specify path; Selenium will handle it
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Handle cookies if needed
    # Example: Add a specific cookie if required by the website
    # driver.add_cookie({'name': 'cookie_name', 'value': 'cookie_value', 'domain': '.lublin.uw.gov.pl'})

    return driver


try:
    # Initialize the Selenium WebDriver with headless options
    driver = setup_selenium_driver()
    logger.info("Selenium WebDriver initialized.")

    # Step 1: Go to the webpage
    driver.get(WEBPAGE_URL)
    logger.info(f"Navigated to {WEBPAGE_URL}. Page title: {driver.title}")
    logger.debug(f"Page source: {driver.page_source[:500]}...")  # Log first 500 characters of page source

    # Optionally handle cookies here if needed
    # Example: Accept cookies if there's a cookie consent banner
    # accept_cookies_button = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.XPATH, '//button[text()="Accept"]'))
    # )
    # accept_cookies_button.click()

    # Step 2: Wait for and click the registration button
    registration_button_xpath = "//button[contains(@class, 'operation-button') and contains(text(), 'Rejestracja – składanie wniosku o legalizację pobytu dla cudzoziemców')]"
    try:
        logger.info("Waiting for registration button...")
        registration_button = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, registration_button_xpath))
        )
        logger.info("Registration button found. Waiting for it to be clickable...")
        registration_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, registration_button_xpath))
        )
        registration_button.click()
        logger.info("Registration button clicked successfully.")
    except Exception as e:
        logger.error(f"Failed to find or click registration button: {e}")
        raise

    # Step 3: Wait for the "Dalej" button and remove any overlays if present
    success = wait_for_dalej_button(driver)
    if not success:
        raise Exception("Failed to click the 'Dalej' button.")

    # Step 4: Check if the specified message is present on the next page
    no_reservations_message_xpath = "//h5[contains(text(), 'Brak dostępnych rezerwacji w okresie')]"
    try:
        logger.info("Checking for reservation message...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, no_reservations_message_xpath))
        )
        logger.info("No available reservations found.")
    except Exception as e:
        logger.warning(f"Error checking for reservation message: {e}")
        # If the element is not found, notify via Telegram
        logger.info("Notification sent via Telegram.")
        message = f"Available reservations found! Check the webpage: {WEBPAGE_URL}"
        asyncio.run(send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message))

finally:
    # Close the browser if driver was successfully initialized
    if 'driver' in locals() and driver is not None:
        driver.quit()
        logger.info("WebDriver quit successfully.")