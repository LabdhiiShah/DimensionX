import os
import time
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


BASE_URL = "http://localhost:5173"


EMPLOYEE_ID = "bhoomi6"
PASSWORD = "bhoomi6"

WAIT_TIME = 15




driver = webdriver.Chrome()
wait = WebDriverWait(driver, WAIT_TIME)

try:
    print("Starting DimensionX Add Project Test")

    # Open the website
    driver.get(BASE_URL)



    get_started = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[self::button or self::a]"
                "[contains(translate(normalize-space(.),"
                "'abcdefghijklmnopqrstuvwxyz',"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),"
                "'GET STARTED')]"
            )
        )
    )
    get_started.click()



    employee_field = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]')
        )
    )

    password_field = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'input[type="password"]')
        )
    )

    employee_field.clear()
    employee_field.send_keys(EMPLOYEE_ID)

    password_field.clear()
    password_field.send_keys(PASSWORD)

    submit_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[@type='submit' "
                "and normalize-space()='SUBMIT']"
            )
        )
    )
    submit_button.click()

    # Wait until the login form disappears
    wait.until(
        EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, 'input[placeholder="name@dimensions"]')
        )
    )

    print("Login successful")

   

    driver.get(BASE_URL + "/projects")

    # Wait for the projects page to load
    wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(.), 'PROJECT HISTORY')]"
            )
        )
    )

    print("Projects page opened")

  

    add_project_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[self::button or self::a]"
                "[contains(translate(normalize-space(.),"
                "'abcdefghijklmnopqrstuvwxyz',"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),"
                "'ADD PROJECT')]"
            )
        )
    )
    add_project_button.click()

    # Wait for the CREATE PROJECT button to appear
    create_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(normalize-space(.), "
                "'CREATE PROJECT')]"
            )
        )
    )

    print("Project creation form opened")



    project_name = "Selenium Project " + uuid.uuid4().hex[:6]

    # Locate the project name field
    project_name_field = wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                'input[placeholder="Sharma residence, 3BHK"]'
            )
        )
    )
    project_name_field.send_keys(project_name)

    # Locate visible inputs within the form
    form = create_button.find_element(By.XPATH, "./ancestor::form")
    inputs = form.find_elements(By.TAG_NAME, "input")

    # The first input is the project name.
    # Fill remaining fields by their expected order.
    text_inputs = [
        field for field in inputs
        if field.get_attribute("type") not in ("date", "hidden", "submit")
    ]

    if len(text_inputs) < 4:
        raise Exception(
            "Could not find all expected project text fields. "
            "Check the form's HTML and input order."
        )

    text_inputs[1].send_keys("Selenium Test Client")
    text_inputs[2].send_keys("selenium@example.com")
    text_inputs[3].send_keys("Selenium Test Designer")

    # Due date
    date_fields = form.find_elements(
        By.CSS_SELECTOR, 'input[type="date"]'
    )
    if date_fields:
        date_field = date_fields[0]

        driver.execute_script(
        """
        arguments[0].value = '2026-12-31';
        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
        """,
        date_field
    )

    # Site address: locate the text input after the date field
    # according to the supplied form structure.
    if len(text_inputs) >= 5:
        text_inputs[4].send_keys("123 Test Street")

    # Description
    description_fields = form.find_elements(By.TAG_NAME, "textarea")
    if description_fields:
        description_fields[0].send_keys(
            "Project created by automated Selenium testing."
        )

 

    create_button.click()

 

    wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                f"//*[contains(normalize-space(.), '{project_name}')]"
            )
        )
    )

    print("TEST PASSED: Project created successfully!")
    print("Project name:", project_name)

except Exception as error:
    print("TEST FAILED:", repr(error))
    print("Current URL:", driver.current_url)
    print("Page title:", driver.title)

finally:
    time.sleep(2)
    driver.quit()
