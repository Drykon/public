"""
Script for backing up Cisco devices.
Then the backups are compared against the last backup taken and diffed.
Script must be run at least twice for the diffing to work so there is something to diff against.
The first run may show an error since there is no previous file for caomparison.
The password is stored in the script as a HASH. This is NOT encrpytion.
Consider writing a way to pull from a password vault instead.
All usage of this file is at your own risk. You've been warned.
"""


# Import time module for appending timestamps to files
import time

# Import Base64 for password hashing
import base64

# Import mkdir and path from OS for folder structure manipulation
from os import mkdir, path, popen

# Import difflib to run the diff of the config files
import difflib

# Import smtplib to facilitate email
import smtplib

# Import Netmiko for Cisco device connections
from netmiko import Netmiko


# Hased password in Base64
passHASH = b'HASH'



def convert(string):
    "Define function with delimeter to use for separating the entries to create the list"
    listv = list(string.split("*"))
    return listv



# Unhash password and store
passByte = base64.b64decode(passHASH)
passWord = passByte.decode('utf-8')



# Device dictionary
# Create a new entry for each device you manage.
# Change the fields accordingly.

# Device 1
dev1 = {
    'host': 'IP or hostname of dev1',
    'username': 'username',
    'password': passWord,
    'device_type': 'cisco_nxos',
}

# Device 2
dev2 = {
    'host': 'IP or hostname of dev2',
    'username': 'username',
    'password': passWord,
    'device_type': 'cisco_ios',
}



# Command(s) to run on the devices
CISCOcommand1 = 'sh start'
CISCOcommand2 = 'sh run'

# Destination email address
toEmailAddress = 'example@example.com'

# Email address used as the "from" email field
fromEmailAddress = 'example@example.com'

# Email server IP
emailServer = 'Email server hostname or IP'

# Email server port
emailServerPort = '25'

# Create time string outside loop
RunT = time.strftime('%Y-%m-%d--%H%M%S')
diffdate = time.strftime('%Y-%m-%d')

# Base folder for saving backups
devBase = '[B:ase\\folder\\for\\backups\\]'

# Set path to DiffTempFolder
DIFFpath = devBase + '\\DiffTempFolder\\'

# Set path for logging error files
ERRpath = devBase + '\\Logs\\'

# Set path to use as the UNC path for links in emails
# Need to use a raw string with these
# UNC path is needed so that the diff HTML files are accessible via user computers.
# This is if the DeviceBackups folder is shared on SERVER_NAME
# Example: r"\\SERVER_NAME\DeviceBackups"
uncPath = r"\\SERVER_NAME\DeviceBackups"

# Set Variable to check for diffing
DiffCheck = 0

# Set Variable to check for error
ErrCheck = 0

# Setting diff file parameters
diff_file = DIFFpath + 'DiffINFO--' + str(diffdate) + '.txt'

# Setting error file parameters
err_file = ERRpath + 'ERROR_INFO--' + str(diffdate) + '.txt'

# Create folder structure
if not path.exists(DIFFpath):
    mkdir(DIFFpath)
if not path.exists(ERRpath):
    mkdir(ERRpath)


# Entry point
if __name__ == '__main__':

    # For loop to run commands per device
    for device in (dev1, dev2):

       # Set variable for detecting like devices
        DeviceType = device['device_type']


        # Execute below script if DeviceType matches a Cisco based OS
        if DeviceType == 'cisco_ios' or DeviceType == 'cisco_nxos' or DeviceType == 'cisco_xe' or DeviceType == 'cisco_asa' or DeviceType == 'dell_force10':

            try:

                # Connection to device and print the prompt
                net_connect = Netmiko(**device)
                # Print device name to terminal
                print('\n' + net_connect.find_prompt())


                # Run command(s)
                CISCOoutput1 = net_connect.send_command(CISCOcommand1)
                CISCOoutput2 = net_connect.send_command(CISCOcommand2)
                
                # Set run time for loop iteration
                timestr = time.strftime('%Y-%m-%d--%H%M%S')
                
                # Determine device hostname and remove extra characters
                find_CISCOhostname = net_connect.find_prompt()
                find_CISCOhostname2 = find_CISCOhostname.replace('/pri/act','')
                find_CISCOhostname3 = find_CISCOhostname2.replace('/sec/act','')
                find_CISCOhostname4 = find_CISCOhostname3.replace('#','')
                CISCOhostname = find_CISCOhostname4.replace('/admin','')
                
                # Disconnect from the session
                net_connect.disconnect()
            
                # Create folder path based on hostname
                CISCOpath = devBase + CISCOhostname + '\\'
                
                # Check for folder with name equal to the device's hostname and create one if not found
                if not path.exists(CISCOpath):
                    mkdir(CISCOpath)
            
                # Save command(s) output to file
                print(CISCOoutput1, file=open(CISCOpath + CISCOhostname + '--STARTUP_CONFIG--' + str(timestr) + '.txt', 'a', encoding="utf-8"))
                print(CISCOoutput2, file=open(CISCOpath + CISCOhostname + '--RUNNING_CONFIG--' + str(timestr) + '.txt', 'a', encoding="utf-8"))

                # Set dir command parameters for Windows based host
                # Replace with Linux substitute if on a Linux based host
                ios_dir = 'dir /B /A:-D /L /O:D ' + CISCOpath

                # Run dir command to pull the directory
                ios_filelist1 = popen(ios_dir).read()

                # Edit results to prepare for converting to a list
                ios_filelist2 = ios_filelist1.replace("\n","*")
                ios_filelist3 = ios_filelist2 + "]"
                ios_filelistTXT = ios_filelist3.replace("*]","")
                
                #Convert dir results to a list
                ios_filelist = (convert(ios_filelistTXT))

                # Remove all entries in the list except ones that contain entries listed in ""
                ios_filelist_running = [ x for x in ios_filelist if "--running_config--" in x ]
                ios_filelist_startup = [ x for x in ios_filelist if "--startup_config--" in x ]


                # Define which files to compare
                iosfile1_running = ios_filelist_running[-2]
                iosfile2_running = ios_filelist_running[-1]
                iosfile1_startup = ios_filelist_startup[-2]
                iosfile2_startup = ios_filelist_startup[-1]
                
                # Convert running configs to list
                first_file_running = CISCOpath + iosfile1_running
                second_file_running = CISCOpath + iosfile2_running
                first_file_lines_running = open(first_file_running, encoding="utf-8").readlines()
                second_file_lines_running = open(second_file_running, encoding="utf-8").readlines()


                # Remove lines in first running config
                first_file_lines_running_1 = [ x for x in first_file_lines_running if "!Time:" not in x ]
                first_file_lines_running_final = [ x for x in first_file_lines_running_1 if "ntp clock-period" not in x ]

                # Remove lines in second running config
                second_file_lines_running_1 = [ x for x in second_file_lines_running if "!Time:" not in x ]
                second_file_lines_running_final = [ x for x in second_file_lines_running_1 if "ntp clock-period" not in x ]
                

                # Convert startup configs to list
                first_file_startup = CISCOpath + iosfile1_startup
                second_file_startup = CISCOpath + iosfile2_startup
                first_file_lines_startup = open(first_file_startup, encoding="utf-8").readlines()
                second_file_lines_startup = open(second_file_startup, encoding="utf-8").readlines()


                # Remove lines in first startup config
                first_file_lines_startup_1 = [ x for x in first_file_lines_startup if "!Time:" not in x ]
                first_file_lines_startup_final = [ x for x in first_file_lines_startup_1 if "ntp clock-period" not in x ]

                # Remove lines in second startup config
                second_file_lines_startup_1 = [ x for x in second_file_lines_startup if "!Time:" not in x ]
                second_file_lines_startup_final = [ x for x in second_file_lines_startup_1 if "ntp clock-period" not in x ]

                # Diff running files and create html report
                if first_file_lines_running_final != second_file_lines_running_final:
                    diff_running = difflib.HtmlDiff().make_file(first_file_lines_running_final, second_file_lines_running_final, first_file_running, second_file_running)
                    diff_file_running = str(CISCOpath + CISCOhostname + '--DIFF_REPORT--RUNNING--' + str(timestr) + '.html')
                    diff_report_running = open(diff_file_running, 'w', encoding="utf-8")
                    diff_report_running.write(diff_running)
                    diff_report_running.close()

                    # Change UNC path for the share
                    ios_diff_unc = diff_file_running.replace(CISCOpath, '')

                    # Creating link to unc path for email
                    print(uncPath + '\\' + CISCOhostname + "\\" + ios_diff_unc, file=open(diff_file, 'a', encoding="utf-8"))

                    # Set DiffCheck variable to 1
                    print('Running config difference(s) detected!')
                    DiffCheck = 1

                else:
                    print('Running files are the same')

                # Diff startup files and create html report
                if first_file_lines_startup_final != second_file_lines_startup_final:
                    diff_startup = difflib.HtmlDiff().make_file(first_file_lines_startup_final, second_file_lines_startup_final, first_file_startup, second_file_startup)
                    diff_file_startup = str(CISCOpath + CISCOhostname + '--DIFF_REPORT--STARTUP--' + str(timestr) + '.html')
                    diff_report_startup = open(diff_file_startup, 'w', encoding="utf-8")
                    diff_report_startup.write(diff_startup)
                    diff_report_startup.close()

                    # Change UNC path for the share
                    ios_diff_unc = diff_file_startup.replace(CISCOpath, '')

                    # Creating link to unc path for email
                    print(uncPath + '\\' + CISCOhostname + "\\" + ios_diff_unc, file=open(diff_file, encoding="utf-8" 'a'))

                    # Set DiffCheck variable to 1
                    print('Startup config difference(s) detected!')
                    DiffCheck = 1

                else:
                    print('Startup files are the same')

            except Exception as e:
                print(str(e) + '\n', file=open(err_file, 'a', encoding="utf-8"))
                print('\n' + str(e))
                ErrCheck = 1



    # Check for any diffing and send email if found  
    if DiffCheck == 1:

        print('\n\n***Gathering email config***')

        # Email configuration
        SUBJECT = 'Nightly backups - Device config changes detected'

        # Gather text for the email
        print('Saving diff_file to variable')
        dif_output = open(diff_file, 'r', encoding="utf-8")
        EMAIL_TEXT = "There were differences found in the configs below:\n\n\n" + dif_output.read()

        server = smtplib.SMTP(emailServer , emailServerPort)
        server.ehlo()

        BODY = '\r\n'.join(['To: %s' % toEmailAddress,
                    'From: %s' % fromEmailAddress,
                    'Subject: %s' % SUBJECT,
                    '', EMAIL_TEXT])

        print('Sending email...')

        try:
            server.sendmail(fromEmailAddress, [toEmailAddress], BODY)
            print ('Email sent.')
        except:
            print ('Error sending mail.')

        server.quit()


    # Check for any diffing and send email if found
    if ErrCheck == 1:

        print('\n\n***Gathering Error email config***')

        # Email configuration
        SUBJECT = 'Nightly backups - Errors detected'

        # Gather text for the email
        print('Saving err_file to variable')
        err_output = open(err_file, 'r', encoding="utf-8")
        EMAIL_TEXT = 'There following errors occurred during the backup process:\n\n\n' + err_output.read()

        server = smtplib.SMTP(emailServer , emailServerPort)
        server.ehlo()

        BODY = '\r\n'.join(['To: %s' % toEmailAddress,
                    'From: %s' % fromEmailAddress,
                    'Subject: %s' % SUBJECT,
                    '', EMAIL_TEXT])

        print('Sending email...')

        try:
            server.sendmail(fromEmailAddress, [toEmailAddress], BODY)
            print ('Email sent.\n\n')
        except:
            print ('Error sending mail.\n\n')

        server.quit()
