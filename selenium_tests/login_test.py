import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.getenv("DIMENSIONX_URL", "http://localhost:5173")
EMPLOYEE_ID = "bhoomi6"
PASSWORD = "bhoomi6"
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

try:
    print("Starting DimensionX Login Test")

    driver.get(BASE_URL)

    # Click GET STARTED on the home page
    get_started = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'GET STARTED')]")
    )
)
    get_started.click()

# Wait for the login form to appear
    employee_field = wait.until(
    EC.visibility_of_element_located(
        (By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]')
     )
        )
    # Locate Employee/Admin ID using the actual HTML placeholder
    employee_field = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]')
        )
    )
    employee_field.send_keys(EMPLOYEE_ID)

    # Locate password using the actual input type
    password_field = driver.find_element(
        By.CSS_SELECTOR, 'input[type="password"]'
    )
    password_field.send_keys(PASSWORD)

    # Locate the actual SUBMIT button
    submit_button = driver.find_element(
        By.XPATH, "//button[@type='submit' and normalize-space()='SUBMIT']"
    )
    submit_button.click()

    # Wait for successful login: URL changes or login form disappears.
    wait.until(
        lambda d: (
            d.current_url.rstrip("/") != BASE_URL.rstrip("/")
            or not d.find_elements(
                By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]'
            )
        )
    )

    # If the login form is still visible, don't report success.
    assert not driver.find_elements(
        By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]'
    ), "Login form is still visible; login may have failed."

    print("TEST PASSED: Login successful")
    print("Current URL:", driver.current_url)

except Exception as error:
    print("TEST FAILED:", error)
    raise

finally:
    driver.quit()
