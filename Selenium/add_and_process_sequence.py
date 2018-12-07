# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

import random
import string
import time
import sys


# random strings

def random_chars(size = None, chars=string.ascii_lowercase):
    size = random.randint(3, 10) if size is None else size
    return ''.join(random.choice(chars) for _ in range(size))

def random_proper():
    return random_chars(size=1, chars=string.ascii_uppercase) + random_chars()

driver = webdriver.Chrome()
#driver = webdriver.Ie()

wait = WebDriverWait(driver, 10)

host_address = "http://localhost:5000/"

def init():
    global host_address
    # Create a new instance of the Firefox driver
    #driver.implicitly_wait(5)

    # go to the home page
    if len(sys.argv) > 1:
        host_address = sys.argv[1]

    driver.get(host_address)

    # make sure we are logged out
    try:
        if driver.find_element_by_partial_link_text("Logout"):
            driver.find_element_by_partial_link_text("Logout").click()
    except NoSuchElementException:
        pass


def main():
    init()


    driver.find_element_by_link_text("Login").click()
    driver.find_element_by_name("email").send_keys('fred@lees.org.uk')
    driver.find_element_by_name("password").send_keys('123456')
    driver.find_element_by_name("submit").click()

    driver.find_element_by_link_text("Sequences").click()
    sub_add_and_process()

def sub_add_and_process():
    # Create a new sequence
    driver.find_element_by_link_text("New Sequence").click()
    wait.until(EC.element_to_be_clickable((By.ID,'new_name')))
    name = random_proper()
    driver.find_element_by_id("new_name").send_keys(name)

    # Select an available inferred sequence from the submissions

    sel_sub = Select(driver.find_element_by_id('submission_id'))
    sub_opts = sel_sub.options

    for sub_opt in sub_opts[1:]:
        sub_opt.click()
        time.sleep(3)
        sel_seq = Select(driver.find_element_by_id('sequence_name'))
        seq_opts = sel_seq.options

        if len(seq_opts) > 0:
            seq_opts[0].click()
            break

    time.sleep(3)
    driver.find_element_by_id('create').click()

    # Edit the new sequence and add the IMGT alignment

    driver.find_element_by_link_text("Sequences").click()
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, name)))
    element = driver.find_element_by_link_text(name)
    element = element.find_element(By.XPATH, "//*[text()[.='%s']]/following-sibling::a" % name).click()

    wait.until(EC.element_to_be_clickable((By.ID, 'coding_seq_imgt')))
    driver.find_element_by_name("coding_seq_imgt").send_keys("""caggtgcagctggtgcagtctggggct---gaggtgaagaagcctggggcctcagtgaag
gtctcctgcaaggcttctggatacaccttc------------accggctactatatgcac
tgggtgcgacaggcccctggacaagggcttgagtggatgggatggatcaaccctaac---
---agtggtggcacaaactatgcacagaagtttcag---ggcagggtcaccatgaccagg
gacacgtccatcagcacagcctacatggagctgagcaggctgagatctgacgacacggcc
gtgtattactgtgcgagaga""")

    # Add another inferred sequence from the edit screen

    driver.find_element_by_xpath('//*[@id="tab-inf"]').click()
    wait.until(EC.element_to_be_clickable((By.ID,'add_inference_btn')))
    driver.find_element_by_id('add_inference_btn').click()

    wait.until(EC.element_to_be_clickable((By.ID, 'submission_id')))
    time.sleep(3)
    sel_sub = Select(driver.find_element_by_id('submission_id'))
    sub_opts = sel_sub.options

    for sub_opt in sub_opts[1:]:
        sub_opt.click()
        time.sleep(3)
        sel_seq = Select(driver.find_element_by_id('sequence_name'))
        seq_opts = sel_seq.options

        if len(seq_opts) > 0:
            seq_opts[0].click()
            break

    time.sleep(3)
    driver.find_element_by_id('create').click()

    # Check the number of inferred sequences and delete one

    wait.until(EC.element_to_be_clickable((By.ID,'add_inference_btn')))
    x = driver.find_elements(By.XPATH, '//*[contains(@class, "delbutton")]')
    assert(len(x) == 2)
    x[random.randint(0, len(x)-1)].click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.ID,'add_inference_btn')))

    # Add some acknowledgements

    driver.find_element_by_xpath('//*[@id="tab-ack"]').click()
    nitems = random.randint(3,5)
    names = [random_proper() + ' ' + random_proper() for i in range(nitems) ]
    insts = [random_proper() + ' ' + random_proper() for i in range(nitems) ]
    orcids = ['0000-0001-9834-6840' if i < (nitems/2) else '' for i in range(nitems)  ]
    for i in range(nitems):
        wait.until(EC.element_to_be_clickable((By.ID,'ack_name')))
        driver.find_element_by_id("ack_name").send_keys(names[i])
        driver.find_element_by_id("ack_institution_name").send_keys(insts[i])
        driver.find_element_by_id("ack_ORCID_id").send_keys(orcids[i])
        driver.find_element_by_id("add_ack").click()

    wait.until(EC.element_to_be_clickable((By.XPATH,'//*[contains(@id, "ack_del_")]')))
    x = driver.find_elements(By.XPATH, '//*[contains(@id, "ack_del_")]')
    assert(len(x) == nitems+1)
    nacks = len(x)
    i = random.randint(0, nitems-1)
    x[i].click()
    wait.until(EC.element_to_be_clickable((By.XPATH,'//*[contains(@id, "ack_del_")]')))
    x = driver.find_elements(By.XPATH, '//*[contains(@id, "ack_del_")]')
    assert(len(x) == nacks-1)

    # Add a note

    driver.find_element_by_xpath('//*[@id="tab-notes"]').click()

    wait.until(EC.element_to_be_clickable((By.ID,'notes')))
    driver.find_element_by_id('notes').send_keys(random_chars(size=random.randint(50,500), chars=string.ascii_lowercase + ' '))
    wait.until(EC.element_to_be_clickable((By.ID,'save_draft_btn')))
    driver.find_element_by_id('save_draft_btn').click()

    # View the draft, and pop up both sequence views

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, name)))
    driver.find_element_by_link_text(name).click()

    wait.until(EC.element_to_be_clickable((By.ID, 'seq_view'))).click()
    time.sleep(3)

    wait.until(EC.element_to_be_clickable((By.CLASS_NAME,'btn-default'))).click()
    time.sleep(3)

    wait.until(EC.element_to_be_clickable((By.ID, 'seq_coding_view'))).click()
    time.sleep(3)

    wait.until(EC.element_to_be_clickable((By.CLASS_NAME,'btn-default'))).click()
    time.sleep(3)

    # Go back to Edit again, and publish

    driver.find_element_by_link_text("Sequences").click()
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, name)))
    element = driver.find_element_by_link_text(name)
    element = element.find_element(By.XPATH, "//*[text()[.='%s']]/following-sibling::a" % name).click()

    wait.until(EC.element_to_be_clickable((By.ID, 'publish_btn')))
    driver.find_element_by_id('publish_btn').click()
    wait.until(EC.element_to_be_clickable((By.ID,'body'))).send_keys('Completed')
    wait.until(EC.element_to_be_clickable((By.ID, 'history_btn'))).click()

    # New draft

    driver.find_element(By.XPATH, "//*[text()[.='%s']]/following-sibling::button" % name).click()
    time.sleep(3)
    el = driver.find_element_by_class_name('btn-warning')
    el.click()

    # Promote

    time.sleep(3)
    element = driver.find_element_by_link_text(name)
    element = element.find_element(By.XPATH, "//*[text()[.='%s']]/following-sibling::a" % name).click()
    wait.until(EC.element_to_be_clickable((By.ID, 'publish_btn')))
    driver.find_element_by_id('publish_btn').click()
    wait.until(EC.element_to_be_clickable((By.ID,'body'))).send_keys('Completed')
    wait.until(EC.element_to_be_clickable((By.ID, 'history_btn'))).click()

    # Withdraw

    driver.find_element(By.XPATH, "//*[text()[.='%s']]/following-sibling::button[2]" % name).click()
    time.sleep(3)
    el = driver.find_element_by_class_name('btn-danger')
    el.click()

if __name__=="__main__":
    main()
    pass




