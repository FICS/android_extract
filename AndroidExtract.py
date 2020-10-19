#!/usr/bin/python3

import os
import os.path
import sys
import subprocess
import argparse
import glob

from subprocess import call
from os.path import expanduser
#from fileinput import filename

##############################################################################################
##############################################################################################
#
# Made by Sam Simon with the generous help of FICS
# Submitted as senior project under Dr. Kevin Butler
# Spring 2020
# 
# Original tool produced in bash by FICS, 
# to check out their amazing tool; please visit link below:
#                  
#             https://github.com/FICS/atcmd/tree/master/extract
#
# For more information and help using this tool, please type "AndroidExtract.py --help"
#
##############################################################################################
##############################################################################################
#
# NOTE: REQUIRED TOOLS:
#           unzip, unrar, 7z, simg2img, mount, dex2jar, xxd, strings, jd-gui, jd-cli
#           baksmali, smali, jadx, unkdz, undz, updata, unsparse,
#           sdat2img, flashtool, sonyelf, imgtool, htcruudec, splitqsb, leszb, unyaffs
#
# NOTE: bingrep is limited and not recommended!
# NOTE: Script does not need to be run as root, but the mounting and unmounting
#       of filesystem images will require sudo privileges
#
# two-column format: 1st column = filename of file containing command,
#                  : 2nd column = AT command.
#
# Ported Python3 code from bash
#
##############################################################################################
##############################################################################################

##########################
#    Global Variables    #
# ---------------------- #
#     Some of these      #
# values are set in main #
##########################

IMAGE = ""
VENDOR = ""
KEEPSTUFF = 0 # keep all the decompiled/unpackaged stuff for later analysis
VENDORMODE = 0 # should be provided as 0 unless alternate mode

HOME = str(expanduser("~"))

EXTUSER = "someuser" # TODO: replace with valid user to use keepstuff functionality
EXTGROUP = "somegroup" # TODO: replace with valid group to use keepstuff functionality
MY_TMP = "extract.sum"
MY_OUT = "extract.db"
MY_USB = "extract.usb"
MY_PROP = "extract.prop"
#MY_TIZ="extract.tizen" # used to mark presence of tizen image(s), replaced by TIZ_LOG
TIZ_LOG = "tizen.log" # samsung
PAC_LOG = "spd_pac.log" # lenovo
SBF_LOG = "sbf.log" # moto
MZF_LOG = "mzf.log" # moto
RAW_LOG = "raw.log" # asus
KDZ_LOG = "kdz.log" # lg
MY_DIR = "extract/" + VENDOR
MY_FULL_DIR = "/data/atdb/extract/" + VENDOR
TOP_DIR = "extract"
AT_CMD = 'AT\+|AT\*'
AT_CMD = 'AT\+|AT\*|AT!|AT@|AT#|AT\$|AT%|AT\^|AT&' # expanding target AT Command symbols
DIR_TMP = ""
MNT_TMP = ""
APK_TMP = ""
ZIP_TMP = ""
ODEX_TMP = ""
TAR_TMP = ""
MSC_TMP = ""
JAR_TMP = "dex.jar"

##############################################################################################

DEPPATH=""
USINGDEPPATH=0 # 1 = true, 0 = false

DEX2JAR=str(DEPPATH)+"/dex2jar/dex-tools/target/dex2jar-2.1-SNAPSHOT/d2j-dex2jar.sh"
JDCLI=str(DEPPATH)+"/jd-cmd/jd-cli/target/jd-cli.jar"
# These are the most recent versions of baksmali/smali that work with java 7 (needed for JADX-nohang)
BAKSMALI=str(DEPPATH)+"/baksmali-2.2b4.jar"
SMALI=str(DEPPATH)+"/smali-2.2b4.jar"
JADX=str(DEPPATH)+"/jadx/build/jadx/bin/jadx"
# ~~~The following tools needed to unpack LG images: avail https://github.com/ehem/kdztools~~~
UNKDZ=str(DEPPATH)+"/kdztools/unkdz"
UNDZ=str(DEPPATH)+"/kdztools/undz"
UPDATA=str(DEPPATH)+"/split_updata.pl/splitupdate"
UNSPARSE=str(DEPPATH)+"combine_unsparse.sh"
SDAT2IMG=str(DEPPATH)+"sdat2img/sdat2img.py"
SONYFLASH=str(DEPPATH)+"flashtool/FlashToolConsole"
SONYELF=str(DEPPATH)+"unpackelf/unpackelf"
IMGTOOL=str(DEPPATH)+"imgtool/imgtool.ELF64"
HTCRUUDEC=str(DEPPATH)+"htcruu-decrypt3.6.5/RUU_Decrypt_Tool" # rename libcurl.so to libcurl.so.4
SPLITQSB=str(DEPPATH)+"split_qsb.pl"
LESZB=str(DEPPATH)+"szbtool/leszb" # szb format1 for lenovo
UNYAFFS=str(DEPPATH)+"unyaffs/unyaffs" # yaffs2 format1 for sony

##############################################################################################

BOOT_OAT = ""
BOOT_OAT_64 = ""
AT_RES = ""
SUB_SUB_TMP = "extract_sub"
SUB_DIR = ""
CHUNKED = 0 # system.img
CHUNKEDO = 0 # oem.img
CHUNKEDU = 0 # userdata.img
COMBINED0 = 0 # system; may be a more elegant solution than this~
COMBINED1 = 0 # userdata
COMBINED2 = 0 # cache
COMBINED3 = 0 # factory or fac
COMBINED4 = 0 # preload
COMBINED5 = 0 # without_carrier_userdata
TARNESTED = 0

#########################
#    Argument Parser    #
#########################

def parse_arguments():
  parser = argparse.ArgumentParser(description = 'Android image extraction tool. Type \'Android Extract -h\' for more information')
  parser.add_argument('-f', dest='filepath', metavar='FIRMWARE IMG FILEPATH', type=str,
    help = 'Path to the top-level packaged archive')
  parser.add_argument('-vendor', dest='vendor', metavar='VENDOR NAME', type=str,
    help = 'The vendor who produced the firmware image (e.g., Samsung, LG)')
  parser.add_argument('-i', dest='index', metavar='INDEX', type=int, 
    help = 'To extract multiple images at the same time, temporary directories will need different indices. For best results, supply an integer value > 0')
  parser.add_argument('-ks', dest='keepstuff', metavar='KEEP STUFF? [0 OR 1]',type=int, 
    help = 'if 0, will remove any extracted files after Processing them;\nif 1, extracted files (e.g., filesystem contents, apps) will be kept')
  parser.add_argument('--vendor-mode', dest='vendormode', metavar='VENDOR MODE [0 OR 1]', type=int, 
    help = 'Supplying 1 as this optional argument will invoke an adjusted extraction')
  
  return parser.parse_args()

##############################################################################################

#########################
#       Help Menu       #
#########################

def print_how_to(): #Help menu
  print("This program must be run with AT LEAST the first 4 of the following options, 5th option is not mandatory:")
  print("-f <FILEPATH>                              : to define package filepath")
  print("-vendor <VENDOR NAME>                      : to define the vendor")
  print("-i <INDEX>                                 : to declare index number of directory")
  print("-ks <KEEP STUFF? [0 OR 1]>                 : to declare whether to remove extracted files after Processing")
  print("--vendor-mode <VENDOR MODE [0 OR 1]>       : to configure specific vendor related settings")

  fo2 = open("2", "wt")

  print("ERROR: not enough arguments provided.",file=fo2)
  print("USAGE: ./atextract.sh <firmware image file> <vendor> <index> <keepstuff flag> <vendor mode (optional)>",file=fo2)
  print("          firmware image file = path to the top-level packaged archive (zip, rar, 7z, kdz, etc.)",file=fo2)
  print("                                (may be absolute or relative path)",file=fo2)
  print("          vendor = the vendor who produced the firmware image (e.g., Samsung, LG)",file=fo2)
  print("                   currently supported = samsung, lg, lenovo, zte, huawei, motorola, asus, aosp,",file=fo2)
  print("                                         nextbit, alcatel, blu, vivo, xiaomi, oneplus, oppo,",file=fo2)
  print("                                         lineage, htc, sony",file=fo2)
  print("          index = to extract multiple images at the same time, temporary directories will",file=fo2)
  print("                  need different indices. For best results, supply an integer value > 0.",file=fo2)
  print("          keepstuff = 0/1",file=fo2)
  print("                      if 0, will remove any extracted files after processing them",file=fo2)
  print("                      if 1, extracted files (e.g., filesystem contents, apps) will be kept",file=fo2)
  print("                            (useful for later manual inspection)",file=fo2)
  print("          vendor mode = some vendors will have several different image packagings",file=fo2)
  print("                        if so, supplying 1 as this optional argument will invoke an adjusted extraction",file=fo2)
  print("                        currently applies to:",file=fo2)
  print("                            password protected Samsung (.zip) image files from firmwarefile.com",file=fo2)
  print("                        extend as needed",file=fo2)
  print("", file=fo2)
  print("For additional guidance and a full list of dependencies, please refer to the provided README.",file=fo2)
  
  fo2.close()

#####################################################################################################################
#####################################################################################################################

#########################
#	   HELPER METHODS	    #
#########################

def clean_up():
  subprocess.run(["sudo", "umount", MNT_TMP, ">", "/dev/null"], shell=True)
  subprocess.run(['rm', '-rf', DIR_TMP, '>', '/dev/null'], shell=True)
  subprocess.run(['rm', '-rf', APK_TMP , '>', '/dev/null'], shell=True)
  subprocess.run(['rm', '-rf', ZIP_TMP , '>', '/dev/null'], shell=True)
  subprocess.run(['rm', '-rf', ODEX_TMP , '>', '/dev/null'], shell=True)
  subprocess.run(['rm', '-rf',  TAR_TMP , '>', '/dev/null'], shell=True)
  subprocess.run(['rm', '-rf',  MSC_TMP , '>', '/dev/null'], shell=True)


# Decompress the zip-like file
# Return 'True' if the decompression is successful
# Otherwise 'False'
# NOTE: to support more decompressing methods, please add them here:

def at_unzip(filename, filename2, directory):
  # filename = "$1"
  # directory = "$2"
  # format = 'file -b "$filename" | cut -d" " -f1'
  
  image_vendor = VENDOR

  format3 = filename[-3:] # 3 character file extensions (i.e. .cpp)
  format4 = filename[-4:] # 4 character file extensions (i.e. .java)
  format5 = filename[-5:] # 5 character file extensions (i.e. .7-zip)
  format6 = filename[-6:] # 6 character file extensions (i.e. .6chars)
  format7 = filename[-7:] # 7 character file extensions (i.e. .7-chars)

  if (filename2 is not None):
    format2_3 = filename2[-3:] # 3 character file extensions (i.e. .cpp)
    format2_4 = filename2[-4:] # 4 character file extensions (i.e. .java)
    format2_5 = filename2[-5:] # 5 character file extensions (i.e. .7-zip)
    format2_6 = filename2[-6:] # 6 character file extensions (i.e. .6chars)
    format2_7 = filename2[-7:] # 7 character file extensions (i.e. .7-chars)


  if (format3 == "zip" ) or (format3 == "ZIP" ) or ( format3 == "Zip" ):
    if directory is None:     
      subprocess.run(['unzip', filename], shell=True)
    else:
      subprocess.run(['unzip', '-d', directory, filename], shell=True)
    AT_RES = "good"
    return True

  elif (format4 == "Java"):
    # mischaracterization of zip file as Java archive data for HTC
    # or it is actually a JAR, but unzip works to extract contents
    if directory is None:     
      subprocess.run(['unzip', filename], shell=True)
    else:
      subprocess.run(['unzip', '-d', directory, filename], shell=True)
    AT_RES = "good"
    return True

  elif (format5 == "POSIX" and format2_3 == "tar"):
    if directory is None:     
      subprocess.run(['tar', 'xvf', filename], shell=True)
    else:
      subprocess.run(['tar','xvf', filename, '-C', directory], shell=True)
    AT_RES = "good"
    return True

  elif (format4 == "PE32" and image_vendor == "htc" ):
    subprocess.run([HTCRUUDEC, '-sf', filename], shell=True)
    decoutput = 'ls | grep \"OUT\"'
    os.rmdir(directory)
    subprocess.run(['mv', decoutput, directory], shell=True)
    AT_RES = "good"
    return True

  elif (format3 == "RAR"):
    if directory is None: 
      subprocess.run(['unrar','x', filename], shell=True)
      if (image_vendor == "samsung"):
        subprocess.run(['tar', 'xvf', 'basename', filename, ".md5"], shell=True)
    else: 
      backfromrar = subprocess.run('pwd', shell=True)
      subprocess.run(['cp', filename, directory], shell=True)
      os.chdir(directory)
      subprocess.run(['unrar','x', filename], shell=True)
      if (image_vendor == "samsung"):
        subprocess.run(['tar', 'xvf', 'basename', filename, ".md5"], shell=True)
      os.remove(filename)
      os.chdir(backfromrar)
    AT_RES = "good"
    return True
  
  elif (format4 == "gzip"):
    # gunzip is difficult to redirect
    if directory is None:
      subprocess.run(['gunzip', filename], shell=True) 
    else:
      backfromgz = subprocess.run('pwd', shell=True)
      subprocess.run(['cp', filename, directory], shell=True)
      subprocess.run(['cd', directory], shell=True)
      subprocess.run(['gunzip', filename], shell=True)
      os.chdir(backfromgz)
    os.remove(filename)
    AT_RES = "good"
    return True
  elif (image_vendor == "motorola" and format7 == ".tar.gz"):
    subprocess.run(['gunzip', filename], shell=True)
    subprocess.run(['tar', 'xvf', 'basename', filename, ".gz"], shell=True)
    AT_RES = "good"
    return True
  elif (image_vendor == "motorola" and format7 == ".tar.gz"):
    backfromgz = subprocess.run('pwd', shell=True)
    subprocess.run(['cp', filename, directory], shell=True)
    subprocess.run(['cd', directory], shell=True)
    subprocess.run(['gunzip', filename], shell=True) 
    subprocess.run(['tar', 'xvf', 'basename', filename, ".gz"], shell=True)
    os.chdir(backfromgz)
    AT_RES = "good"
    return True
  
  elif (format5 == "7-zip"):
    if directory is None:
      subprocess.run(['7z', 'x', filename], shell=True)
    else:
      subprocess.run(['unrar', 'x', '-o', directory, filename], shell=True)
    AT_RES = "good"
    return True

  else:
    AT_RES = "bad"
    return False


# We are in sub_sub_dir
def handle_text(filename):
  #	grep $AT_CMD $1 >> ../$MY_TMP
	subprocess.run(['grep', '-E', AT_CMD, '\"', filename, '\"', ' | ', 'awk', '-v', 'fname=\"', filename, '\" BEGIN {OFS=\"\t\"} {print fname,$0} >> ', MY_TMP], shell=True) #mod-filenameprint

def handle_binary(filename):
  #	strings -a $1 | grep $AT_CMD >> ../$MY_TMP
	subprocess.run(['grep', '-E', AT_CMD, '\"', filename, '\"', ' | ', 'awk', '-v', 'fname=\"', filename, '\" BEGIN {OFS=\"\t\"} {print fname,$0} >> ', MY_TMP], shell=True) #mod-filenameprint

def handle_elf(filename):
	handle_binary(filename)
	# Can run bingrep, elfparser but they suck...

def handle_x86(filename):
	# Currently no special handling for x86 boot sectors
	handle_binary(filename)

def handle_bootimg(filename):
  name = str(subprocess.run(["basename ", filename], shell=True))
  if (name[4:] == "boot" or
        name[8:] == "recovery" or
        name[4:] == "hosd" or
        name[9:] == "droidboot" or
        name[8:] == "fastboot" or
        name[10:] == "okrecovery" or
        name[4:] == "BOOT" or
        name[8:] == "RECOVERY" or
        name[-4:] == ".bin" ):
    subprocess.run([IMGTOOL, filename, "extract"], shell=True)
    os.chdir("extracted")
    format_ = subprocess.run(["file","-b","ramdisk", "|", "cut", "-d", " ", "-f1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
    if (format_ == "LZ4"):
      subprocess.run(["unlz4", "ramdisk", "ramdisk.out"], shell=True)
      subprocess.run(["cat", "ramdisk.out", "|", "cpio", "-i"], shell=True)
      os.remove('ramdisk.out')
    elif (format_ == "gzip"):
      subprocess.run(["gunzip", "-c", "ramdisk", "|", "cpio", "-i"], shell=True)
    os.remove("ramdisk")
    os.chdir("..")
    find_out = subprocess.run(["find","extracted", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
    for line in find_out:
      if (os.path.isfile(line)):
        format_ = subprocess.run(["file","-b","ramdisk", "|", "cut", "-d", " ", "-f1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        if (format_ == "gzip"):
          subprocess.run(["mv", line, line, ".gz"], shell=True)
          subprocess.run(["gunzip", "-f", line, ".gz"], shell=True)
          at_extract(line)
        else:
          at_extract(line)
        print(line + "processed: " + AT_RES)
    # ------------------------------------------
    # Need corresponding piped while loop FIXME
    # ------------------------------------------
    if ( KEEPSTUFF == 1 ):
      subprocess.run(["sudo", "cp", "-r", "extracted", MY_FULL_DIR + "/" + SUB_DIR + "/" + name], shell=True)
      subprocess.run(["sudo", "chown", "-R", EXTUSER + ":" + EXTGROUP, MY_FULL_DIR + "/" + SUB_DIR + "/" + name], shell=True)
    os.rmdir("extracted")
  else:
    handle_binary(filename)

def handle_zip(filename, filetype):
  rtn = ""
  print("Unzipping " + filename + " ...")
  os.mkdir(ZIP_TMP)
  subprocess.run(["cp",filename, ZIP_TMP] ,shell=True)
  if (filetype == "zip"):
    subprocess.run(["unzip","-d",str(ZIP_TMP),str(ZIP_TMP)+"/"+filename],shell=True)
  elif (filetype == "gzip"):
    if (filename[-7:] == ".img.gz"):
      print("Handling a .img.gz file... ")
      gzip = subprocess.run(["basename", filename, ".gz"], shell=True)
      subprocess.run("gunzip" + " " + "-c" + " " + str(ZIP_TMP)+"/"+filename,shell=True,stdout=open(str(ZIP_TMP)+"/"+str(gzip),'wb'))
    else:
      print("Handling a .tar.gz file... ")
      subprocess.run(["tar","xvf",str(ZIP_TMP)+"/"+filename,"-C",str(ZIP_TMP)],shell=True)
    os.rmdir(ZIP_TMP+"/"+filename)
    # ------------------------------------------
    # Need corresponding piped while loop FIXME
    # ------------------------------------------
    if (KEEPSTUFF == 1):
      subprocess.run(["sudo","cp","-r",str(ZIP_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+filename],shell=True)
      subprocess.run(["sudo","chown","-R",str(EXTUSER)+":"+str(EXTGROUP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+filename],shell=True)
    os.rmdir(ZIP_TMP+"/"+filename)

def handle_qsbszb(qsbszb, qsmode):
  getback = str(os.getcwd())
  os.mkdir(MSC_TMP)
  subprocess.run(["cp",str(qsbszb),str(MSC_TMP)],shell=True)
  qsbszb = os.popen("basename \""+str(qsbszb)+"\"").read().rstrip("\n")
  os.chdir(MSC_TMP)
  if (qsmode == 0):
    print("Splitting qsb " + str(qsbszb) + " ...")
    subprocess.run([str(SPLITQSB), str(qsbszb)], shell=True)
  else:
    print("Splitting szb " + str(qsbszb) + " ...")
    subprocess.run([str(LESZB), "-x", str(qsbszb)], shell=True)
  os.remove(qsbszb)
  # ------------------------------------------
  # Need corresponding piped while loop FIXME
  # ------------------------------------------
  os.chdir(getback)
  os.rmdir(MSC_TMP)

def handle_apk(apk):
  name = os.popen("basename \""+str(apk)+"\"").read().rstrip("\n")
  print("Decompiling" + str(name) + " ...")
  os.mkdir(APK_TMP)
  subprocess.run(["cp",str(apk),str(APK_TMP)+"/"+str(name)],shell=True) # Dex2Jar
  subprocess.run([str(DEX2JAR),str(APK_TMP)+"/"+str(name),"-o",str(APK_TMP)+"/"+str(JAR_TMP)],shell=True)
  subprocess.run("java" + " " + "-jar" + " " + str(JDCLI) + " " + "-oc" + " " + str(APK_TMP)+"/"+str(JAR_TMP),shell=True,stdout=open(str(APK_TMP)+"/jdcli.out",'wb'))
  subprocess.run(["grep","-E",str(AT_CMD),str(APK_TMP)+"/jdcli.out"],shell=True)
  subprocess.run("awk" + " " + "-v" + " " + "apkname="+str(name) + " " + "BEGIN {OFS=\"\\t\"} {print apkname,$0}",shell=True,stdout=open(str(MY_TMP),'ab'))
  if (KEEPSTUFF == 1 ):
    subprocess.run(["cp","-r",str(APK_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(name)],shell=True)
  os.rmdir(APK_TMP)
  
def handle_jar(filename):
  subprocess.run(["java","-jar",str(JDCLI),"-oc",str(filename)],shell=True)
  subprocess.run(["grep","-E",str(AT_CMD)],shell=True)
  subprocess.run("awk" + " " + "-v" + " " + "fname="+str(filename) + " " + "BEGIN {OFS=\"\\t\"} {print fname,$0}",shell=True,stdout=open(str(MY_TMP),'ab'))

def handle_java(filename):
  format4 = str(filename)[-4:]
  if (format4 == ".apk" or format4 == ".APK" or format4 == ".Apk"):
    handle_apk(filename)
  else:
    handle_jar(filename)

def handle_odex(odex):
  name = os.popen("basename \""+str(odex)+"\"").read().rstrip("\n")
  arch = ""
  boot = ""
  print("Processing odex...")
  os.mkdir(ODEX_TMP)
  subprocess.run(["cp",str(odex),str(ODEX_TMP)+"/"+str(name)],shell=True) # Dex2Jar

  arch = str(os.popen("file -b "+str(ODEX_TMP)+"/\""+str(name)+"\" | cut -d\" \" -f2 | cut -d\"-\" -f1").read().rstrip("\n"))
  if (arch == "64"):
    boot = BOOT_OAT_64
  else:
    boot = BOOT_OAT
  print("DEBUG: use boot.oat - " + boot)

  if (boot is not ""):
    print("Processing smali...")
    # Try to recover some strings from smali
    subprocess.run(["java","-jar",str(BAKSMALI),"deodex","-b",str(boot),str(ODEX_TMP)+"/"+str(name),"-o",str(ODEX_TMP)+"/out"],shell=True)
    # grep -r $AT_CMD $ODEX_TMP/out >> ../$MY_TMP
    ret = subprocess.run(["grep","-r","-E",str(AT_CMD),str(ODEX_TMP)+"/out"],shell=True)
    subprocess.run("awk" + " " + "-v" + " " + "fname="+str(ret) + " " + "BEGIN {OFS=\"\\t\"} {print fname,$0}",shell=True,stdout=open(str(MY_TMP),'ab'))
    # Try to decompile from smali->dex->jar->src
		# May not work!
    print("decompiling smali/dex...")
    subprocess.run(["java","-jar",str(SMALI),"ass",str(ODEX_TMP)+"/out","-o",str(ODEX_TMP)+"/out.dex"],shell=True)
    print("invoking jadx on smali/dex output...")
    subprocess.run([str(JADX),"-d",str(ODEX_TMP)+"/out2",str(ODEX_TMP)+"/out.dex"],shell=True)
    if (os.path.isdir(str(ODEX_TMP)+"/out2")):
      subprocess.run(["grep","-r","-E",str(AT_CMD),str(ODEX_TMP)+"/out2"],shell=True)
      subprocess.run("awk" + " " + "-v" + " " + "fname="+str(name) + " " + "BEGIN {OFS=\"\\t\"} {print fname,$0}",shell=True,stdout=open(str(MY_TMP),'ab'))
    if (KEEPSTUFF == 1):
      subprocess.run(["cp","-r",str(ODEX_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(name)],shell=True)
    os.rmdir(ODEX_TMP)
    
def check_for_suffix(filename):
  suffix = filename[-4:]
  suffix2 = filename[-5:]
  
  if (suffix == ".apk" or suffix == ".APK" or suffix == ".Apk"
        or suffix == ".jar" or suffix == ".Jar" or suffix == ".JAR"):
    AT_RES = "java"
  elif (suffix2 == ".odex" or suffix2 == ".ODEX" or suffix2 == ".Odex"):
    AT_RES == "odex"
  else:
    AT_RES = "TBD"

# Process special files
# All files which require special care should happen here
def handle_special(filename):
  justname = str(os.popen("basename \""+str(filename)+"\"").read().rstrip("\n"))

  usbFile = open(MY_USB)
  propFile = open(MY_PROP)
  tizFile = open(TIZ_LOG)

  if (justname == str(glob.glob("init*usb.rc"))):
    # Save init file for USB config analysis
    # also need to capture e.g., init.hosd.usb.rc (notable: aosp sailfish)
    # there's also init.tuna.usb.rc in aosp yakju, etc.
    # init.steelhead.usb.rc in tungsten
    print(filename, file = usbFile)
    print("---------",file = usbFile)
    subprocess.run("cat" + " " + str(filename),shell=True,stdout=usbFile)
    print("=========",file=usbFile)

  elif (justname == "build.prop" ):
    # Save the contents of build.prop to get information about OS version, etc.
    print(filename,file=propFile)
    print("---------",file=propFile)
    # in rare cases, permission denied when trying to access build.prop
    subprocess.run("sudo" + " " + "cat" + " " + str(filename),shell=True,stdout=propFile)
    print("=========",file=propFile)

  elif ( VENDOR == "samsung" ) and ( justname == "dzImage" ):
    # Tizen OS image detected. Should abort
    # touch ../$MY_TIZ
    AT_RES = "tizen"
    print(str(filename)+" processed: "+str(AT_RES))
    print(IMAGE,file=tizFile)
    # for easier ID later, needs to be existing file
    exit(55)
    # exit immediately; no need to go further
  
def at_extract(filename):
  filetype = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
  justname = (os.popen("basename \""+str(filename)+"\"").read().rstrip("\n"))
  
  # Check for special files
  handle_special(filename)
  
  if (filetype == "apollo" or filetype == "FoxPro" or filetype == "Mach-O" or
        filetype == "DOS/MBR" or filetype == "PE32" or filetype == "PE32+" or 
        filetype == "dBase" or filetype == "MS" or filetype == "PDP-11" or 
        filetype == "zlib" or filetype == "ISO-8859" or filetype == "Composite" or 
        filetype == "very" or filetype == "Hitachi" or filetype == "SQLite" ):
    handle_binary(filename)
    AT_RES = "good"
  elif (filetype == "ELF"):
    handle_elf(filename)
    check_for_suffix(filename)
    if (AT_RES == "odex"):
      handle_odex(filename)
    AT_RES = "good"
  elif (filetype == "x86"):
    handle_x86(filename)
    AT_RES = "good"
  elif (filetype == "DOS"):
    handle_text(filename)
    AT_RES = "good"
  elif (filetype == "Java"):
    handle_java(filename)
    AT_RES = "good"
  elif (filetype == "POSIX" or filetype == "Bourne-Again"):
    handle_text(filename)
    AT_RES = "good"
  elif (filetype == "ASCII" or filetype == "XML" or filetype == "Tex" or filetype == "html"
          or filetype == "UTF-8" or filetype == "C" or filetype == "Pascal" or filetype == "python"):
    handle_text(filename)
    AT_RES = "good"
  elif (filetype == "Windows"):
    handle_text(filename)
    AT_RES = "good"
  elif (filetype == "Zip"):
    check_for_suffix(filename)
    if ("AT_RES" == "java"):
      handle_java(filename)
      AT_RES = "good"
    else:
      handle_zip(filename, "zip")
      AT_RES = "good"
  elif (filetype == "gzip" or filetype == "XZ"):
    handle_zip(filename, "gzip")
    AT_RES = "good"
  elif (format == "Android"):
    print("Processing .img file as binary!")
    handle_bootimg(filename)
    AT_RES = "good"
  elif (format == "broken" or format == "symbolic" or format == "SE" or 
          format == "empty" or format == "directory" or format == "Ogg" or
          format == "PNG" or format == "JPEG" or format == "PEM" or 
          format == "TrueType" or format == "LLVM" or format == "Device"):
    # format == dBase was being skipped before; now handled as binary (jochoi)
		# format == Device Tree Blob after extracting boot/recovery img; ignoring
		# Skip broken/symbolic/sepolicy/empty/dir/...
    AT_RES = "skip"
  else:
    AT_RES = "bad"

def handle_ext4(imgPath):
  ext = str(os.popen("basename \""+str(imgPath)+"\"").read().rstrip("\n"))
  arch = ""
  os.mkdir(DIR_TMP)
  os.mkdir(MNT_TMP)
  # Make a copy
  subprocess.run(["cp",imgPath,DIR_TMP+"/"+(ext)],shell=True)
  # NOTE: needs sudo or root permission
  subprocess.run(["sudo","mount","-t","ext4",(DIR_TMP)+"/"+str(ext),str(MNT_TMP)],shell=True)
  subprocess.run(["sudo","chown","-R",(EXTUSER)+":"+(EXTGROUP),str(MNT_TMP)],shell=True)
  # Find the boot.oat for RE odex
  BOOT_OAT = ""
  BOOT_OAT_64 = ""

  thisFile = open("newfile.txt")

  while open(thisFile):
    # Debug
    #echo "DEBUG: boot.oat - $file"
    arch = str(os.popen("file -b \""+str(thisFile)+"\" | cut -d\" \" -f2 | cut -d\"-\" -f1").read().rstrip("\n"))
    if (arch == "64"):
      BOOT_OAT_64=thisFile
    else:
      BOOT_OAT=thisFile

  subprocess.run("arch" + " " + "find" + " " + str(MNT_TMP) + " " + "-name" + " " + "boot.oat" + " " + "-print",shell=True,stdin=open("sudo", 'rb'))
  print("found boot.oat: "+str(BOOT_OAT)+", boot_oat(64): "+str(BOOT_OAT_64))
  # Traverse the filesystem - root permission
  find_out = subprocess.run(["find", MNT_TMP, "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
  for line in find_out:
    if (os.path.isfile(line)):
      at_extract(line)
      print(line + " processed: " + AT_RES)
  # what we're interested is probably the contents of the FS once mounted, rather than DIR_TMP
  if ( "$KEEPSTUFF" == "1" ):
    #		cp -r $DIR_TMP ../$ext
    subprocess.run(["sudo","cp","-r",str(MNT_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
    subprocess.run(["sudo","chown","-R",str(EXTUSER)+":"+str(EXTGROUP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
  
  subprocess.run(["sudo","umount",str(MNT_TMP)],shell=True)
  os.rmdir(DIR_TMP)
  AT_RES = ("good")

def handle_chunk(imgFile, chunkMode):
  # need the directory name, not the specific file name
  ext= "system.img"
  raw="system.img.raw"
  container = str(os.popen("dirname \""+str(imgFile)+"\"").read().rstrip("\n"))
  arch = ""
  getback = str(os.popen("pwd").read().rstrip("\n"))
  chunkdir = "system_raw"

  # needs to be performed from within the directory
  os.chdir(container) # simg2img must be performed from within the directory
  os.mkdir(chunkdir)
  subprocess.run(["cp",glob.glob("system.img_*"),str(chunkdir)],shell=True)
  os.chdir(chunkdir)
  subprocess.run(["simg2img",(glob.glob("*chunk*")),str(raw)],shell=True)
  subprocess.run(["file",str(raw)],shell=True)
  print("Stage 1 complete")
  if (chunkMode == 0):
    subprocess.run(["offset","=",os.popen("LANG=C grep -aobP -m1 \"\\x53\\xEF\" "+str(raw)+" | head -1 | gawk \"{print $1 - 1080}\"").read().rstrip("\n")],shell=True)
  elif (chunkMode == 1):
    subprocess.run(["mv",str(raw),str(ext)],shell=True) # no further Processing needed
  print("Stage 2 complete")
  subprocess.run(["mv", ext, ".."],shell=True)
  os.chdir("..")
  os.rmdir(chunkdir)
  os.chdir(str(getback)) # return to directory of the script
  
  handle_ext4(container + "/" + ext)

def handle_chunk_lax(imgFile, chunkMode):
  container=str(os.popen("dirname \""+str(imgFile)+"\"").read().rstrip("\n"))
  getback=str(os.popen("pwd").read().rstrip("\n"))
  ext = ""
  chunkdir = ""

  os.chdir(container)

  if (chunkMode == 0):
    chunkdir = "oem_raw"
    os.mkdir(chunkdir)
    subprocess.run(["cp",str(glob.glob("oem.img_*")),str(chunkdir)],shell=True)
    ext = "oem.img"
  elif(chunkMode == 1):
    chunkdir = "userdata_raw"
    os.mkdir(chunkdir)
    subprocess.run(["cp",str(glob.glob("userdata.img_*")),str(chunkdir)],shell=True)
    ext = "userdata.img"
  elif (chunkMode == 2):
    chunkdir = "systemb_raw"
    os.mkdir(chunkdir)
    subprocess.run(["cp",str(glob.glob("systemb.img_*")),str(chunkdir)],shell=True)
    ext = "systemb.img"

  os.chdir(str(chunkdir))
  subprocess.run(["simg2img",(glob.glob("*chunk*")),str(ext)],shell=True)
  subprocess.run(["mv",str(ext),".."],shell=True)
  os.chdir("..")
  os.rmdir(chunkdir)
  os.chdir(str(getback))

  handle_ext4(container + "/" + ext)

def handle_sdat(img, path):
  container=str(os.popen("dirname \""+str(img)+"\"").read().rstrip("\n"))
  SDAT2IMG = "$container" + "/" + path + ".transfer.list" + img + container + "/" + ".img"
  handle_ext4(container + "/" + path + ".img")

def handle_sin(img):
  fullimg= str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(SUB_SUB_DIR)+"/"+os.popen("ls \""+str(img)+"\" | cut -d \"/\" -f2-").read().rstrip("\n")
  container=str(os.popen("dirname \""+str(img)+"\"").read().rstrip("\n"))
  base=str(os.popen("basename \""+str(img)+"\" .sin").read().rstrip("\n"))
  subprocess.run([str(SONYFLASH),"--action=extract","--file="+str(fullimg)],shell=True) # will write to directory containing the img
  getback=str(os.popen("pwd").read().rstrip("\n"))
  
  # the result is observed to be ext4, elf, or unknown formats~
  if (base[-5:] == ".ext4"):
    handle_ext4(container + "/" + base + ".ext4")
  elif (base[-4:] == ".elf"):
    # need to specially manage kernel.elf
    if (base == "kernel"):
      print("Processing separate ramdisk img")
      print("-----------------------------")
      os.chdir(str(container))
      os.mkdir("elfseperate")
      subprocess.run(["mv","kernel.elf","elfseparate"],shell=True)
      os.chdir("elfseparate")
      subprocess.run([str(SONYELF),"-i","kernel.elf","-k","-r"],shell=True)
      os.mkdir("ramdiskseparate")
      subprocess.run(["mv","kernel.elf-ramdisk.cpio.gz","ramdiskseparate"],shell=True)
      os.chdir("ramdiskseparate")
      pipe1, pipe2 = os.pipe()
      if os.fork():
          os.close(pipe1)
          os.dup2(pipe1, 0)
          subprocess.run(["cpio","-i"],shell=True)
      else:
          os.close(pipe1)
          os.dup2(pipe1, 1)
          subprocess.run(["gunzip","-c","kernel.elf-ramdisk.cpio.gz"],shell=True)
          sys.exit(0)
      os.remove("kernel.elf-ramdisk.cpio.gz")
      os.chdir("..")
      find_out = subprocess.run(["find","ramdiskseparate", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
      for line in find_out:
        if (os.path.isfile(line)):
          at_extract(line)
          print(line + "processed: " + AT_RES)
      os.rmdir("ramdiskseparate")
      os.chdir(getback)
      print("-----------------------------")
    else:
      at_extract((container + "/" + base + ".elf"))
  elif(base[-4:] == ".yaffs2"):
    print("Processing yaffs2 img")
    print("-----------------------------")
    os.chdir(str(container))
    os.mkdir("yaffsseperate")
    subprocess.run(["mv",str(base)+".yaffs2","yaffsseparate"],shell=True)
    os.chdir("yaffsseparate")
    UNYAFFS = base + ".yaffs2"
    os.remove(base + ".yaffs2")
    find_out = subprocess.run(["find",".", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
    for line in find_out:
      if (os.path.isfile(line)):
        at_extract(line)
        print(line + "processed: " + AT_RES)
    os.chdir(getback)
    print("--------------------------")
  else:
    at_extract((container + "/" + base + ".unknown"))
  
  #currently not working FIXME
def handle_vfat(img):
  ext = str(os.popen("basename \""+str(img)+"\"").read().rstrip("\n"))
  arch = ""
  os.mkdir(DIR_TMP)
  os.mkdir(MNT_TMP)
  # Make a copy
  subprocess.run(["cp", str(img), str(DIR_TMP)+"/"+str(ext)],shell=True)
  # NOTE: needs sudo or root permission
  subprocess.run(["sudo", "mount", "-t", "vfat", str(DIR_TMP)+"/"+str(ext), str(MNT_TMP)],shell=True)
  subprocess.run(["sudo", "chown", "-R", str(EXTUSER) + ":" + str(EXTGROUP), str(MNT_TMP)],shell=True)
  # Find the boot.oat for RE odex
  BOOT_OAT=""
  BOOT_OAT_64= ""

  thisFile = open()

  while open(thisFile):
    # Debug
    #echo "DEBUG: boot.oat - $file"
    arch = str(os.popen("file -b \""+str(thisFile)+"\" | cut -d\" \" -f2 | cut -d\"-\" -f1").read().rstrip("\n"))
    if (arch == "64"):
      BOOT_OAT_64=thisFile
    else:
      BOOT_OAT=thisFile
    
    #Need while loop for at_extract FIXME
    if (KEEPSTUFF == 1):
      subprocess.run(["sudo","cp","-r",str(MNT_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
      subprocess.run(["sudo","chown","-R",str(EXTUSER)+":"+str(EXTGROUP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
    
    subprocess.run(["sudo","umount",str(MNT_TMP)],shell=True)
    os.rmdir(DIR_TMP)
    AT_RES = "good"

def handle_simg(img):
  nam = str(os.popen("basename -s .img \""+str(img)+"\"").read().rstrip("\n"))
  ext = str(nam)+".ext4"
  arch = ""
  os.mkdir(DIR_TMP)
  os.mkdir(MNT_TMP)
  subprocess.run(["simg2img",str(img),str(DIR_TMP)+"/"+str(ext)],shell=True)
  # NOTE: needs sudo or root permission
  subprocess.run(["sudo","mount","-t","ext4",str(DIR_TMP)+"/"+str(ext),str(MNT_TMP)],shell=True)
  subprocess.run(["sudo","chown","-R",str(EXTUSER)+":"+str(EXTGROUP),str(MNT_TMP)],shell=True)
  # Find the boot.oat for RE odex
  BOOT_OAT= ""
  BOOT_OAT_64= ""

  ######################################
  # Need corresponding while loop FIXME
  ######################################
  
  # Traverse the filesystem - root permission
  subprocess.run(["sudo","find",str(MNT_TMP),"-print0"],shell=True)

  find_out = subprocess.run(["find", MNT_TMP, "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
  for line in find_out:
    if (os.path.isfile(line)):
      at_extract(line)
      print(line + "processed: " + AT_RES)
  
  if (KEEPSTUFF == 1):
    subprocess.run(["sudo","cp","-r",str(MNT_TMP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
    subprocess.run(["sudo","chown","-R",str(EXTUSER)+":"+str(EXTGROUP),str(MY_FULL_DIR)+"/"+str(SUB_DIR)+"/"+str(ext)],shell=True)
  
  subprocess.run(["sudo","umount",str(MNT_TMP)],shell=True)
  os.rmdir(DIR_TMP)
  AT_RES = "good"

def handle_unsparse(filename, prefix, xmlFile, imageVendor):
  # handle_unsparse(filename, "system", "rawprogram0.xml", VENDOR)
  container=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
  
  UNSPARSE = container + prefix + xmlFile + imageVendor
  handle_ext4(container + "/" + prefix + ".img")

# Go thru each from within sub_sub_dir
# Currently no special handling for bootloader.img, radio.img and modem.img
def process_file(filename):
  justname = str(os.popen("basename \""+str(filename)+"\"").read().rstrip("\n"))
  #	local format=`file -b $filename | cut -d" " -f1`
  handled = False
  #	echo "Processing file: $filename" >> ../$MY_TMP # printing out the file being processed
  #	echo "IN process_file | handling file: $filename"
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS AOSP
  #-------------------------------------------------------------------------------
  if (VENDOR == "aosp"):
    if (justname == "system.img" or justname == "system_other.img" or justname == "vendor.img"):
      #  Handle sparse ext4 fs image
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    else:
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Samsung
  #-------------------------------------------------------------------------------
  elif (VENDOR == "samsung"):
    samformat = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
    if (( justname == "persist.img.ext4" ) or ( justname == "system.img.ext4" ) or ( justname == "cache.img.ext4" ) or 
            ( justname == "omr.img.ext4" ) or ( justname == "userdata.img.ext4" ) ):
      if (samformat == "Linux"):
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
      else:
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
      handled = True
    elif ( (justname == "cache.img" ) or ( justname == "hidden.img" ) or ( justname == "omr.img" ) 
            or ( justname == "hidden.img.md5" ) or ( justname == "cache.img.md5" ) or ( justname == "persist.img" ) 
            or ( justname == "factoryfs.img" ) ):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
    elif ( (justname == "system.img" ) or ( justname == "userdata.img" ) or ( justname == "system.img.md5" ) 
            or ( justname == "userdata.img.md5" ) ):
      if (samformat == "DOS/MBR"):
        print("Processing vfat img...")
        print("-----------------------------")
        handle_vfat(filename)
        print("-----------------------------")
      else:
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
      handled = True
    elif (justname == "adspso.bin"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif ( (justname == "system.rfs" ) or ( justname == "csc.rfs" ) or ( justname == "efs.img" ) 
            or ( justname == "factoryfs.rfs" ) or ( justname == "cache.rfs" ) or ( justname == "hidden.rfs" ) ):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "fota.zip"):
      print("WARNING: Skipping password-protected fota.zip!")
      handled = True
    elif ( justname == glob.glob("*.tar*") or justname == glob.glob("*.TAR*") ):
      TARNESTED=((TARNESTED + 1))
      # increment TARNESTED
      os.mkdir("nestedPOSIXtar"+str(TARNESTED))
      ret = subprocess.run(["tar","xvf",str(filename),"-C","nestedPOSIXtar"+str(TARNESTED)],shell=True)
      #need recursive loop FIXME
      if str(ret) == "55":
          exit(55)
      print("-------------------------")
      os.rmdir("nestedPOSIXtar"+str(TARNESTED))
      TARNESTED=((TARNESTED - 1))
      handled = True
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Motorola
  #-------------------------------------------------------------------------------
  elif (VENDOR == "motorola"):
    motoformat = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
    if (justname == str(glob.glob("*.sbf"))):
      # proprietary motorola format
			# the only available tool, sbf_flash, is unreliable, skip and record only FIXME
      print(IMAGE, file=open(SBF_LOG))
    elif (justname == str(glob.glob("*.mzf"))):
      # unclear how to extract from .mzf (no tools found) FIXME
      print(IMAGE, file=open(MZF_LOG))
      # not attempting to deal with shx or nb0 files either (5)
		  # nb0 utils unpacker simply unpacks as data, not imgs
    elif (justname == str(glob.glob("system.img_sparsechunk.*"))):
      if (CHUNKED == 0):
        print("Processing sparsechunks into ext4...")
        print("-----------------------------")
        handle_chunk(filename, 0)
        CHUNKED = 1 # no need to duplicate work per sparsechunk
        print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("system.img_sparsechunk*"))):
      # NOTE: this if does not include the period as last elif
      if (CHUNKED == 0):
        print("Processing sparsechunks into ext4...")
        print("-----------------------------")
        handle_chunk(filename, 1)
        CHUNKED=1 # no need to duplicate work per sparsechunk
        print("-----------------------------")
    elif (justname == str(glob.glob("oem.img_sparsechunk.*"))):
      if (CHUNKEDO == 0):
        print("Processing sparsechunks into ext4...")
        print("-----------------------------")
        handle_chunk_lax(filename, 0)
        CHUNKEDO=1 # no need to duplicate work per sparsechunk
        print("-----------------------------")
    elif (justname == str(glob.glob("userdata.img_sparsechunk*"))):
      if (CHUNKEDU == 0):
        print("Processing sparsechunks into ext4...")
        print("-----------------------------")
        handle_chunk_lax(filename, 1)
        CHUNKEDU=1 # no need to duplicate work per sparsechunk
        print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("system_b.img_sparsechunk.*"))):
      if (CHUNKEDB == 0):
        print("Processing sparsechunks into ext4...")
        print("-----------------------------")
        handle_chunk_lax(filename, 1)
        CHUNKEDU=1 # no need to duplicate work per sparsechunk
        print("-----------------------------")
      handled = True
    elif ( (justname == "adspo.bin") or (justname == "fsg.mbn" ) or (justname == "preinstall.img" ) or (justname == "radio.img" ) ):
      # Handle ext4 fs image
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif ( (justname == "system_signed") or (justname == "modem_signed") ):
      if (motoformat == "Linux"): #FIXME in bash script spelled as "motoformaat"
        # Handle ext4 fs image
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
        handled = True
    elif ( (justname == "BTFM.bin") or (justname == "cache.img") or (justname == "preload.img") ):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "NON-HLOS.bin"):
      if (motoformat == "Linux"):
        # Handle ext4 fs image
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
      elif (motoformat == "Android"):
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
      handled = True
    # not all images follow the sparsechunk; may be sparseimg already
    elif (justname == "system.img"):
    # ignore; want to avoid double work of handle_chunk
      if (CHUNKED == 1):
        print("not Processing system_b.img (handled by handle_chunk)...")
      else:
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
      handled = True
    elif (justname == "system.new.dat"):
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Nextbit
  #-------------------------------------------------------------------------------
  elif (VENDOR == "nextbit"):
    # NextBit phone firmware shares the characteristics of aosp (only system.img needs to be handled as simg)
    # however, there are some additional .img files which need to be processed as binaries (not simg or ext4)
    if (justname == "system.img" or justname == str(glob.glob("*persist.img")) or justname == "*cache.img" or justname == "*hidden.img.ext4"):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS LG
  #-------------------------------------------------------------------------------
  elif (VENDOR == "lg"):
    if ( justname == "system.image" ) or (justname == "userdata.image" ) or (justname == "cache.image" ) or (justname == "cust.image" ) or (justname == str(glob.glob("persist_*.bin")) ):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    # newly downloaded LG firmware (bumped) matching physical device has different names
    # for firmwares as zip; not expected to use these for the kdz extraction
    elif (justname == str(glob.glob("*modem_*.bin"))):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "system.img"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "modem.img"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS LG
  #-------------------------------------------------------------------------------
  elif (VENDOR == "htc"):
    # HTC Firmware (first 3 are observed in both ZIP and RUU-EXE) have a few vfat mountables
    if (justname == "wcnss.img" ) or (justname == "adsp.img" ) or (justname == "radio.img" ) or (justname == "cpe.img" ) or (justname == "venus.img" ) or (justname == "slpi.img" ) or (justname == "rfg_3.img" ) or (justname == "bluetooth.img" ):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    # ~~~ start EXE-specific handling
    # ~~~ the existence of or proper formatting of other ~.img varies across firmwares
    elif (justname == "system.img" ) or (justname == "appreload.img" ) or (justname == "cota.img" ) or (justname == "cache.img" ) or (justname == "dsp.img" ):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("userdata*.img")) or justname == "persist.img"):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "ramdisk.img"):
      print("Processing seperate ramdisk img...")
      print("-----------------------------")
      os.mkdir("ramdiskseparate")
      subprocess.run(["mv","ramdisk.img","ramdiskseparate"],shell=True)
      os.chdir("ramdiskseparate")
      p1, p2 = os.pipe()
      if os.fork():
          os.close(p1)
          os.dup2(p2, 0)
          subprocess.run(["cpio","-i"],shell=True)
      else:
          os.close(p2)
          os.dup2(p1, 1)
          subprocess.run(["gunzip","-c","ramdisk.img"],shell=True)
          sys.exit(0)
      os.remove("ramdisk.img")
      os.chdir("..")
      find_out = subprocess.run(["find","ramdiskseparate", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
      for line in find_out:
        if (os.path.isfile(line)):
          at_extract(line)
          print(line + "processed: " + AT_RES)
      os.rmdir("ramdiskseparate")
      print("-----------------------------")
      handled = True

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Blu
  #-------------------------------------------------------------------------------
  elif (VENDOR == "blu"):
    # ext4 = cache.img, system.img, userdata.img; these are also the only mountables (ext4)
    if ( justname == "system.img") or (justname == "cache.img") or (justname == "userdata.img" ):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Huawei
  #-------------------------------------------------------------------------------
  elif (VENDOR == "huawei"):
    # TODO: USERDATA.img does not mount after simg2img Processing; did updata fail?
    # TODO: no current handling for ~~~-sign.img. Only 5 firmwares of this form
    # ----: not obvious how to handle these, unfortunately
    # NOTE: no mountable vfat was found
    if ( justname == "CACHE.img") or (justname == "USERDATA.img") or (justname == "PERSIST.img") or (justname == "cust.img") or (justname == "persist.img") or (justname == "modem.img") or (justname == "nvm1.img") or (justname == "nvm2.img") or (justname == "TOMBSTONES.img") or (justname == "MODEMIMAGE.img"):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "cache.img") or (justname == "userdata.img"):
      huaformat = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
      # prioritize Android simg
      if (huaformat == "Android"):
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
        handled = True
      # below elif not correct FIXME
      elif ("-e" == str(glob.glob(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n")+"/*scatter*.txt"))):
        print("Processing unusual ext4 img by padding...")
        print("-----------------------------")
        lbindir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
        subprocess.run(["dd","if=/dev/zero","of="+str(lbindir)+"/padding.zer","bs="+os.popen("ls -l \""+str(filename)+"\" | awk \"{ print $5 }\"").read().rstrip("\n"),"count=1"],shell=True)
        subprocess.run("cat" + " " + str(lbindir)+"/padding.zer",shell=True,stdout=open(str(filename)))
        os.remove(str(lbindir)+"/padding.zer")
        handle_ext4(filename)
        print("-----------------------------")
      handled = True
    elif (justname == "system.img" ) or (justname == "SYSTEM.img" ) or (justname == "CUST.img" ):
      # need special handling, because it may sometimes be simg, othertimes ext4
      # it may actually even fail when it is ext4 (too complex to handl here)
      # --- on those failing firmwares, cache, userdata also affected
      # --- example: Huawei_Honor_H30-T10-MT6572_20131216_4.2.2
      huaformat = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
      # may have additional name, e.g., MT6582_Android_scatter-Hol-U10-16GB.txt
      # prioritize Android simg
      if (huaformat == "Android"):
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
        handled = True
      # below elif not correct FIXME
      elif ("-e" == str(glob.glob(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n")+"/*scatter*.txt"))):
        print("Processing unusual ext4 img by padding...")
        print("-----------------------------")
        lbindir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
        subprocess.run(["dd","if=/dev/zero","of="+str(lbindir)+"/padding.zer","bs="+os.popen("ls -l \""+str(filename)+"\" | awk \"{ print $5 }\"").read().rstrip("\n"),"count=1"],shell=True)
        subprocess.run("cat" + " " + str(lbindir)+"/padding.zer",shell=True,stdout=open(str(filename)))
        os.remove(str(lbindir)+"/padding.zer")
        handle_ext4(filename)
        print("-----------------------------")
        handled = True
      elif (huaformat == "Linux"):
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
        handled = True
    elif (justname == "system.bin" ) or (justname == "userdata.bin" ) or (justname == "cache.bin" ) or (justname == "protect_s.bin" ) or (justname == "protect_f.bin"):
      # rare case for huawei
      print("Processing unusual ext4 img by padding...")
      print("-----------------------------")
      lbindir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
      subprocess.run(["dd","if=/dev/zero","of="+str(lbindir)+"/padding.zer","bs="+os.popen("ls -l \""+str(filename)+"\" | awk \"{ print $5 }\"").read().rstrip("\n"),"count=1"],shell=True)
      subprocess.run("cat" + " " + str(lbindir)+"/padding.zer",shell=True,stdout=open(str(filename)))
      os.remove(str(lbindir)+"/padding.zer")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("system_*.unsparse"))):
      if (COMBINED0 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "system", "rawprogram0.xml", VENDOR)
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    elif (justname == str(glob.glob("userdata_*.unsparse"))):
      if (COMBINED1 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "userdata", "rawprogram0.xml", VENDOR)
        print("-----------------------------")
        COMBINED1 = 1
      handled = True
    elif (justname == str(glob.glob("cache_*.unsparse"))):
      print("Processing cache unsparse ext4 img...")
      print("-----------------------------")
      lcachdir = str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
      if ((int)(os.popen("ls \""+lcachdir+"\"/\"cache_*\"").read().rstrip("\n")) == 1):
        subprocess.run(["dd","if=/dev/zero","of="+str(lcachdir)+"/cache.zer","bs=512","count=246488"],shell=True)
        subprocess.run("cat" + " " + str(lcachdir)+"/cache.zer",shell=True,stdout=open(str(filename),'ab'))
        os.remove(lcachdir+"/"+"cache.zer")
        handle_ext4(filename)
        print("-----------------------------")
      else:
        if (COMBINED2 == 0):
          print("Processing unsparse ext4 img...")
          print("-----------------------------")
          handle_unsparse(filename, "cache", "rawprogram0.xml", VENDOR)
          print("-----------------------------")
          COMBINED2 = 1
      handled = True
    elif (justname == str(glob.glob("system_*.img"))):
      if (COMBINED2 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "system", "rawprogram0.xml", VENDOR)
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    elif (justname == str(glob.glob("userdata_*.img"))):
      if (COMBINED1 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "userdata", "rawprogram0.xml", VENDOR)
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    elif (justname == str(glob.glob("cache_*.img"))):
      print("Processing cache unsparse ext4 img...")
      print("-----------------------------")
      lcachdir = str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
      if ((int)(os.popen("ls \""+lcachdir+"\"/\"cache_*\"").read().rstrip("\n")) == 1):
        subprocess.run(["dd","if=/dev/zero","of="+str(lcachdir)+"/cache.zer","bs=512","count=246488"],shell=True)
        subprocess.run("cat" + " " + str(lcachdir)+"/cache.zer",shell=True,stdout=open(str(filename),'ab'))
        os.remove(lcachdir+"/"+"cache.zer")
        handle_ext4(filename)
        print("-----------------------------")
      else:
        if (COMBINED2 == 0):
          print("Processing unsparse ext4 img...")
          print("-----------------------------")
          handle_unsparse(filename, "cache", "rawprogram0.xml", VENDOR)
          print("-----------------------------")
          COMBINED2 = 1
      handled = True
    elif (justname == str(glob.glob("persist_*.unsparse" ))) or (justname == str(glob.glob("persist_*.img"))):
      print("Processing unsparse ext4 img...")
      print("-----------------------------")
      lpersdir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
      subprocess.run(["dd","if=/dev/zero","of="+lpsersdir+"/persist.zer","bs=512","count=56120"],shell=True)
      # magic number found by comparison with a persist.img in some ROMs
      subprocess.run("cat" + " " + str(lpersdir)+"/persist.zer",shell=True,stdout=open(str(filename),'ab'))
      subprocess.run(["rm",str(lpersdir)+"/persist.zer"],shell=True)
      handle_ext4(filename)
      print("-----------------------------")
    elif (justname == "NON-HLOS.bin" ) or (justname == "MODEM.img" ) or (justname == "log.img" ) or (justname == "fat.img" ) or (justname == "fat.bin"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("*.pac"))):
      print(IMAGE, file=open(PAC_LOG))
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Lenoveo
  #-------------------------------------------------------------------------------
  elif (VENDOR == "lenovo"):
    if (justname == "system.img") or (justname == "userdata.img") or (justname == "cache.img") or (justname == "persist.img") or (justname == "fac.img") or (justname == "config.img") or (justname == "factory.img") or (justname == "country.img") or (justname == "preload.img") or (justname == "cpimage.img"):
      lenformat = str(os.popen("file -b \""+filename+"\" | cut -d\" \" -f1").read().rstrip("\n"))
      if (lenformat == "Android"):
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
        handled = True
      elif (lenformat == "Linux"):
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
        handled = True
    elif (justname == "adspso.bin") or (justname == "countrycode.img") or (justname == "system.img.ext4.unsparse"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "userdata.img.ext4") or (justname == "without_carrier_cache.img") or (justname == str(glob.glob("*.rom"))):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "BTFM.bin") or (justname == "NON-HLOS.bin") or (justname == "fat.bin") or (justname == "udisk.bin"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    # Handle split up pieces of system_#.img, userdata_#.img, cache_#.img, persist_#.img, preload_#.img
		# Prevent duplicate processing
    elif (justname == str(glob.glob("system_*.img"))):
      if (COMBINED0 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "system", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "system", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "system", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "system", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    elif (justname == str(glob.glob("userdata_*.img"))):
      if (COMBINED1 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "userdata", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "userdata", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "userdata", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "userdata", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED1 = 1
      handled = True
    elif (justname == str(glob.glob("without_carrier_userdat_*.img"))):
      if (COMBINED5 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "without_carrier_userdata", "rawprogram_unsparse_clean_carrier.xml", VENDOR)
        print("-----------------------------")
        COMBINED5 = 1
      handled = True
    elif (justname == str(glob.glob("cache_*.img"))):
      lcachdir = str(os.popen("dirname \""+ filename))
      #FIXME if statement (`ls "$lcachdir"/"cache_*"` -eq 1) needed
      if (COMBINED2 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "cache", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "cache", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "cache", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "cache", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED2 = 1
      handled = True
    elif (justname == str(glob.glob("system_*.unsparse"))):
      if (COMBINED0 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "system", "rawprogram0.xml", VENDOR + str(2))
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    elif (justname == str(glob.glob("userdata_*.unsparse"))):
      if (COMBINED1 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "userdata", "rawprogram0.xml", VENDOR + str(2))
        print("-----------------------------")
        COMBINED1 = 1
      handled = True
    elif (justname == str(glob.glob("cache_*.unsparse"))):
      lcachdir = str(os.popen("dirname \""+ filename))
      #FIXME if statement (`ls "$lcachdir"/"cache_*"` -eq 1) needed
      if (COMBINED2 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "cache", "rawprogram0.xml", VENDOR + str(2))
        print("-----------------------------")
        COMBINED2 = 1
      handled = True
    elif (justname == "persist_*.img") or (justname == "persist_*.unsparse"):
      print("Processing persist unsparse ext4 img...")
      print("-----------------------------")
      lpersdir=str(os.popen("dirname \""+str(filename)+"\""))
      subprocess.run(["dd","if=/dev/zero","of="+str(lpersdir)+"/persist.zer","bs=512","count=56120"],shell=True)
      # magic number found by comparison with a persist.img in some ROMs
      subprocess.run("cat" + " " + str(lpersdir)+"/persist.zer",shell=True,stdout=open(str(filename),'ab'))
      os.remove(lpersdir + "/persist.zer")
      handle_ext4(filename)
      # handle_unsparse $filename "persist" "rawprogram_unsparse.xml" "$VENDOR"
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("factory_*.img"))):
      if (COMBINED3 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "factory", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "factory", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "factory", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "factory", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED3 = 1
      handled = True
    elif (justname == str(glob.glob("fac_*.img"))):
      if (COMBINED3 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "fac", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "fac", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "fac", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "fac", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED3 = 1
      handled = True
    elif (justname == str(glob.glob("preload_*.img"))):
      if (COMBINED4 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram_unsparse.xml")):
          handle_unsparse(filename, "preload", "rawprogram_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "preload", "rawprogram0_unsparse.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0.xml")):
          handle_unsparse(filename, "preload", "rawprogram0.xml", VENDOR)
        elif (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/upgrade.xml")):
          handle_unsparse(filename, "preload", "upgrade.xml", VENDOR)
        print("-----------------------------")
        COMBINED4 = 1
      handled = True
    elif (justname == "system.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
    elif (justname == "data.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "data")
      print("-----------------------------")
      handled = True
    elif (justname == "ramdisk.img") or (justname == "ramdisk-recovery.img"):
      print("Processing seperate ramdisk img...")
      print("-----------------------------")
      os.mkdir("ramdiskseparate")
      subprocess.run(["mv","ramdisk.img","ramdiskseparate"],shell=True)
      os.chdir("ramdiskseparate")
      subprocess.run(["gunzip","-c", "ramdisk.img", "|", "cpio", "-i"],shell=True)
      os.remove("ramdisk.img")
      os.chdir("..")
      find_out = subprocess.run(["find","ramdiskseparate", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
      for line in find_out:
        if (os.path.isfile(line)):
          at_extract(line)
          print(line + "processed: " + AT_RES)
      os.rmdir("ramdiskseparate")
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("*.qsb"))):
      print("Processing qsb archive...")
      print("-----------------------------")
      handle_qsbzb(filename, 0)
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("*.szb"))):
      print("Processing szb archive...")
      print("-----------------------------")
      handle_qsbzb(filename, 1)
      print("-----------------------------")
      handled = True
    elif (justname == "system.img.gz"):
      subprocess.run(["gunzip", "system.img.gz"], shell=True)
      print("Processing ext4 img...")
      print("-----------------------------")
      temp = subprocess.run(["basename", filename, ".gz"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      handle_ext4(subprocess.run(["dirname", filename+"/"+temp],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("systemchunk*.img"))):
      getback = os.getcwd()
      path = subprocess.run(["dirname", filename],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      os.chdir(path)
      subprocess.run(["simg2img", "*chunk*", "system.img"], shell=True)
      os.remove("systemchunk.img")
      os.chdir(getback)
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(subprocess.run(["dirname", filename+"/system.img"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("*.pac"))):
      print(IMAGE, file=open(PAC_LOG))
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS oneplus
  #-------------------------------------------------------------------------------
  elif (VENDOR == "oneplus"):
    if (justname == "adspso.bin"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "NON-HLOS.bin") or (justname == "BTFM.bin"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "system.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Sony
  #-------------------------------------------------------------------------------
  elif (VENDOR == "sony"):
    # FLASHTOOL: need special tool for *.sin, *.sinb, and *.ta extracted from the ftf archive
		# Debugged the CLI version; requires modification of SWT variable
		# kernel.sin, loader.sin, partition-image.sin, system.sin, userdata.sin,
		# -- cache.sin, apps_log.sin, amss_fsg.sin, amss_fs_1.sin, amss_fs_2.sin
    if (justname == str(glob.glob("*.sin"))) or (justname == str(glob.glob("*.sinb"))):
      print("Processing sin img...")
      print("-----------------------------")
      handle_sin(filename)
      print("-----------------------------")
      handled = True
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Vivo
  #-------------------------------------------------------------------------------
  elif (VENDOR == "vivo"):
    if (justname == "adspso.bin"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "NON-HLOS.bin") or (justname == "BTFM.bin"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    # FIXME:
    # Handle split up pieces of system_#.img, userdata_#.img, cache_#.img, preload_#.img
		# Prevent duplicate processing
		# further unsparse combining deferred as not dealing with vivo now
    if justname == str(glob.glob("system_*.img")):
      if (COMBINED0 == 0):
        print("processing unsparse ext4 img...")
        print("-----------------------------")
        handle_unsparse(filename, "system", "rawprogram_unsparse.xml", VENDOR) # FIXME: not supported
        print("-----------------------------")
        COMBINED0 = 1
      handled = True
    ####################################
    # Other split ups unimplemented here
    ####################################
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS ZTE
  #-------------------------------------------------------------------------------
  elif (VENDOR == "zte"):
    # FIXME (?) Ignoring single ROM with ZTE One Key Upgrade Tool exe
    if (justname == "adspso.bin"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "NON-HLOS.bin") or (justname == "BTFM.bin") or (justname == "fat.img") or (justname == "fat.bin"):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "system.bin" ) or (justname == "userdata.bin" ) or (justname == "cache.bin" ) or (justname == "protect_s.bin" ) or (justname == "protect_f.bin" ):
      print("Processing unusual ext4 img by padding...")
      print("-----------------------------")
      lbindir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
      subprocess.run(["dd","if=/dev/zero","of="+str(lbindir)+"/padding.zer","bs="+os.popen("ls -l \""+str(filename)+"\" | awk \"{ print $5 }\"").read().rstrip("\n"),"count=1"],shell=True)
      subprocess.run("cat" + " " + str(lbindir)+"/padding.zer",shell=True,stdout=open(str(filename)))
      os.remove(str(lbindir)+"/padding.zer")
      handle_ext4(filename)
      print("-----------------------------")
    elif (justname == "system_*.img"):
      # zte's unsparse system image follows lenovo's technique
      if (COMBINED0 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "system", "rawprogram0_unsparse.xml", "lenovo")
        else:
          handle_unsparse(filename, "system", "rawprogram_unsparse.xml", "lenovo")
        print("-----------------------------")
        COMBINED0=1
      handled = True
    elif (justname == "userdata_*.img"):
      if (COMBINED1 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "userdata", "rawprogram0_unsparse.xml", VENDOR)
        else:
          handle_unsparse(filename, "userdata", "rawprogram_unsparse.xml", VENDOR)
        print("-----------------------------")
        COMBINED1=1
      handled = True
    elif (justname == "cache*.img"):
      # zte's unsparse system image follows lenovo's technique
      if (COMBINED2 == 0):
        print("Processing unsparse ext4 img...")
        print("-----------------------------")
        if (os.path.isfile(os.popen("dirname \""+ filename + "\"")+"/rawprogram0_unsparse.xml")):
          handle_unsparse(filename, "cache", "rawprogram0_unsparse.xml", VENDOR)
        else:
          handle_unsparse(filename, "cache", "rawprogram_unsparse.xml", VENDOR)
        print("-----------------------------")
        COMBINED2=1
      handled = True
    elif (justname == "persist_*.img") or (justname == "persist_*.unsparse"):
      print("Processing persist unsparse ext4 img...")
      print("-----------------------------")
      lpersdir=str(os.popen("dirname \""+str(filename)+"\""))
      subprocess.run(["dd","if=/dev/zero","of="+str(lpersdir)+"/persist.zer","bs=512","count=56120"],shell=True)
      # magic number found by comparison with a persist.img in some ROMs
      subprocess.run("cat" + " " + str(lpersdir)+"/persist.zer",shell=True,stdout=open(str(filename),'ab'))
      os.remove(lpersdir + "/persist.zer")
      handle_ext4(filename)
      # handle_unsparse $filename "persist" "rawprogram_unsparse.xml" "$VENDOR"
      print("-----------------------------")
      handled = True
    elif (justname == "system.img") or (justname == "userdata.img") or (justname == "cache.img") or (justname == "protect_s.img") or (justname == "protect_f.img"):
      zteformat = str(os.popen("file -b \""+str(filename)+"\" | cut -d\" \" -f1").read().rstrip("\n"))
      if (os.path.isfile(subprocess.run(["dirname", filename + "/scatter.txt"]))):
        print("Processing unusual ext4 img by padding...")
        print("Processing unusual ext4 img by padding...")
        print("-----------------------------")
        lbindir=str(os.popen("dirname \""+str(filename)+"\"").read().rstrip("\n"))
        subprocess.run(["dd","if=/dev/zero","of="+str(lbindir)+"/padding.zer","bs="+os.popen("ls -l \""+str(filename)+"\" | awk \"{ print $5 }\"").read().rstrip("\n"),"count=1"],shell=True)
        subprocess.run("cat" + " " + str(lbindir)+"/padding.zer",shell=True,stdout=open(str(filename)))
        os.remove(str(lbindir)+"/padding.zer")
        handle_ext4(filename)
      elif (zteformat == "Android"):
        print("Processing sparse ext4 img...")
        print("-----------------------------")
        handle_simg(filename)
        print("-----------------------------")
        handled = True
      elif (zteformat == "Linux"):
        print("Processing ext4 img...")
        print("-----------------------------")
        handle_ext4(filename)
        print("-----------------------------")
        handled = True
      handled = True
    elif (justname == "system.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
    elif (justname == "ramdisk.img_raw"):
      print("Processing seperate ramdisk img...")
      print("-----------------------------")
      os.mkdir("ramdiskseparate")
      subprocess.run(["mv","ramdisk.img","ramdiskseparate"],shell=True)
      os.chdir("ramdiskseparate")
      subprocess.run(["gunzip","-c", "ramdisk.img", "|", "cpio", "-i"],shell=True)
      os.remove("ramdisk.img")
      os.chdir("..")
      find_out = subprocess.run(["find","ramdiskseparate", "-print0"],universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.split_lines()
      for line in find_out:
        if (os.path.isfile(line)):
          at_extract(line)
          print(line + "processed: " + AT_RES)
      os.rmdir("ramdiskseparate")
      print("-----------------------------")
      handled = True
    elif (justname == str(glob.glob("*.pac"))):
      print(IMAGE, file=open(PAC_LOG))
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Lineage
  #-------------------------------------------------------------------------------
  elif (VENDOR == "lineage"):
    if (justname == "system.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Asus
  #-------------------------------------------------------------------------------
  elif (VENDOR == "asus"):
    if (justname == "asusfw.img") or (justname == str(glob.glob("adspso.bin"))) or (justname == "APD.img") or (justname == "ADF.img") or (justname == "factory.img"):
      print("Processing ext4 img...")
      print("-----------------------------")
      handle_ext4(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "system.img"):
      print("Processing sparse ext4 img...")
      print("-----------------------------")
      handle_simg(filename)
      print("-----------------------------")
      handled = True
    elif (justname == "system.new.dat"):
      # maybe needed for system.patch.dat (though this has been found empty)
      print("Processing sdat img...")
      print("-----------------------------")
      handle_sdat(filename, "system")
      print("-----------------------------")
      handled = True
    elif (zteformat == str(glob.glob("*NON-HOLOS*.bin"))):
      print("Processing vfat img...")
      print("-----------------------------")
      handle_vfat(filename)
      print("-----------------------------")
      handled = True
  #---------------------------------------------------------------------------------
  if (handled is False):
    at_extract(filename)
  #----------------------------------------------------------------------------------


#####################################################################################################################
######################################               ################################################################
######################################     MAIN      ################################################################
######################################               ################################################################
#####################################################################################################################


def main():

  args = parse_arguments()

  # if no args
  
  if (args.filepath is not None and args.vendor is not None):
    IMAGE = args.filepath
    VENDOR = args.vendor
    KEEPSTUFF = (args.keepstuff) # keep all the decompiled/unpackaged stuff for later analysis
    VENDORMODE = (args.vendormode) # should be provided as 0 unless alternate mode

    DIR_TMP = HOME + "/atsh_tmp" + str(args.index)
    MNT_TMP = HOME + "/atsh_tmp" + str(args.index) + "/mnt"
    APK_TMP = HOME + "/atsh_apk" + str(args.index)
    ZIP_TMP = HOME + "/atsh_zip" + str(args.index)
    ODEX_TMP = HOME + "/atsh_odex" + str(args.index)
    TAR_TMP = HOME + "/atsh_tar" + str(args.index)
    MSC_TMP = HOME + "/atsh_msc" + str(args.index)

  use_UI = False
  temp_str = "error"

  #####################################################################################################################
  
  print()
  print("---------------------------------------------------")
  print("Welcome to Sam Simon's Android extraction tool!")
  print("----------------------------------------------------------")
  print()
  print("Please enter (Y/N) for whether or not you would like to use the interactive")
  print("UI to run this program or simply have already (or want to) use the command argument input")
  print()
  
  while (temp_str == "error"):
    print("   (\'Y\' to use UI guide or \'N\' to not use UI guide): ")
    temp_str = input()
    if (temp_str == "Y"):
      use_UI = True
      print("Sorry the current UI mode is not working, please restart program with command line input!")
      print("Type \'exit\' to leave cleanly or enter any key if want to continue anyway: ")
      temp_str = input()
      if (temp_str == "exit"):
        exit(0)
    elif (temp_str == "N"):
      use_UI = False
    else:
      temp_str = "error"
  
  print("**********************************************************")
  print()
  print("This tool was created in cohesion with FICS. The tool is based of a previous iteration")
  print("   of andriod extraction where AT commands were pulled from Andriod image files.")
  print()
  print("For more information on the previous tool, please visit:")
  print("            www.atcommands.org")
  print()
  print("**********************************************************")
  print()
  print()
  
  #####################################################################################################################

  if (use_UI is True):
    print("Welcome to the UI for Sam's Android Extraction Tool!")
    print("----------------------------------------------------------")
    print()
    print("Please enter in a option from below:")
    print("1. Load Andriod Image file via path")
    print("2. Retreive Andriod Image file via Google Drive")
    print("3. Run pre-made script on file via path")
    
    scriptType = -99
    choice = -99
    while (choice == -99):
      print()
      print("Your choice: ")
      str_choice = ""
      str_choice = input()
      choice = int(str_choice)
      if (choice <= 0 or choice > 3):
        choice = -99

    filepath = ""
    print()
    if (choice == 1):
      print("---------------------------------------------------")
      print("Please enter in file path: ")
      filepath = input()
      print ("Sorry, this option is currently not working right now!")
      print("---------------------------------------------------")
      exit(0)
    elif (choice == 2):
      print("---------------------------------------------------")
      print ("Sorry, this option is currently not working right now!")
      # print("Please enter in a google drive file http share link: ")
      # input(filepath)
      print("---------------------------------------------------")
      exit(0)
    elif (choice == 3):
      print("---------------------------------------------------")
      print("Please enter in a file path to designated shell or python script: ")
      filepath = input()
      print()
      print("---------------------------------------------------")
      print("Is this a Python or Bash script?")
      print("   (0 = Python // 1 = Bash):")
      scriptType = int(input())
      if (scriptType != 0) and (scriptType != 1):
        print()
        print("Sorry, this option is currently not working right now!")
        print("---------------------------------------------------")
      print("Sorry, this option is currently not working right now!")
      print("---------------------------------------------------")
      exit(0)
    quit()
  
  print("================================================================")
  print("================================================================")
  print("================================================================")
  print()
  print()
  
  #####################################################################################################################
  
  # if dependencies have not been updated (deppath = "")
  
  fo2 = open("2", "wt")

  if (USINGDEPPATH == 1 ) and (DEPPATH == "" ):
    print("ERROR: variable DEPPATH not initialized on line 64",file=fo2)
    print("     : if not using DEPPATH and manually updated all dependency locations on lines 67-85",file=fo2)
    print("     : set USINGDEPPATH=0 to disable this check.",file=fo2)
    print("",file=fo2)
    print("For additional guidance and a full list of dependencies, please refer to the provided README.",file=fo2)
    exit(1)
  
  # print usage if not enough arguments provided
  if (args.filepath is None or args.vendor is None or args.index is None or args.vendormode is None):
    print_how_to()
    print()
    print()
    exit(0)
  elif (args.vendormode == 0):
    print("WARN : VENDERMODE has been set to 0!")
    print("WARN : some images may require alternative steps for extraction, in which case you should supply",file=fo2)
    print("       an additional argument (1). currently applies to:",file=fo2)
    print("                        password protected Samsung (.zip) image files from firmwarefile.com",file=fo2)
    print("       Continuing after defaulting to 0!",file=fo2)
    print()
    VENDORMODE = 0
  
  #####################################################################################################################
  
  print("ALERT: Now initiating extraction process")
  
  os.mkdir(TOP_DIR)
  os.mkdir(MY_DIR)
  subprocess.run(["cp", IMAGE, MY_DIR])
  os.chdir(MY_DIR)

  VENDOR = subprocess.run(["basename", VENDOR, "-expanded"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
  print("The current vendor: " + VENDOR)

  if (VENDOR == "samsung"):
    if (not os.path.isfile(TIZ_LOG)):
      open(TIZ_LOG, "w+")
    TIZ_LOG = os.getcwd() + "/" + TIZ_LOG
  elif (VENDOR == "lenovo") or (VENDOR == "zte") or (VENDOR == "huawei"):
    if (not os.path.isfile(PAC_LOG)):
      open(PAC_LOG, "w+")
    PAC_LOG = os.getcwd() + "/" + PAC_LOG
  elif (VENDOR == "motorola"):
    if (not os.path.isfile(SBF_LOG)):
      open(SBF_LOG, "w+")
    SBF_LOG = os.getcwd() + "/" + SBF_LOG
    if (not os.path.isfile(MZF_LOG)):
      open(MZF_LOG, "w+")
    MZF_LOG = os.getcwd() + "/" + MZF_LOG
  elif (VENDOR == "asus"):
    if (not os.path.isfile(RAW_LOG)):
      open(RAW_LOG, "w+")
    RAW_LOG = os.getcwd() + "/" + RAW_LOG
  elif (VENDOR == "lg"):
    if (not os.path.isfile(KDZ_LOG)):
      open(KDZ_LOG, "w+")
    KDZ_LOG = os.getcwd() + "/" + KDZ_LOG

  IMAGE = subprocess.run(["basename", VENDOR], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")

  #####################################################################################################################
  
  print("ALERT: Cleaning up temporary files from prior run (if any).")
  clean_up()

  #####################################################################################################################
  
  # Assume name.suffix format
  if (VENDOR == "asus"):
    DIR_PRE= subprocess.run(["echo", IMAGE, "|", "cut", "-d", "?", "-f", "1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
    SUB_EXT = DIR_PRE[-4:]
    SUB_DIR = DIR_pre[:-4]
  else:
    SUB_EXT = DIR_PRE[-4:]
    SUB_DIR = DIR_pre[:-4]

  print("Output will be available in: " + SUB_DIR)
  os.mkdir(SUB_DIR)
  subprocess.run(["mv", IMAGE, SUB_DIR])
  os.chdir(SUB_DIR)

  #####################################################################################################################
  # try to unzip
  #####################################################################################################################
  #####################################################################################################################
  
  print("Unzipping the image file...")
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS AOSP
  #-------------------------------------------------------------------------------
  if (VENDOR == "aosp"):
    at_unzip(IMAGE, None, None)
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Samsung
  #-------------------------------------------------------------------------------
  elif (VENDOR == "samsung"):
    os.mkdir(SUB_SUB_TMP)
    DECSUFFIX = IMAGE[-4:]
    if (DECSUFFIX == ".zip"):
      if (VENDORMODE == "1"):
        subprocess.run(["7z", "x", "-p", "firmwarefile.com", "-o", SUB_SUB_TMP, IMAGE])
      else:
        at_unzip(IMAGE, None, SUB_SUB_TMP)
    elif (DECSUFFIX == ".rar"):
      subprocess.run(["cp", IMAGE, SUB_SUB_TMP])
      os.chdir(SUB_SUB_TMP)
      subprocess.run(["unrar", "e", "-o+", IMAGE])
      os.remove(IMAGE)
      os.chdir("..")
    elif (DECSUFFIX == str(glob.glob("*.7z"))):
      subprocess.run(["7z", "x", "-o", SUB_SUB_TMP, IMAGE])
    os.chdir(SUB_SUB_TMP)
    # Need to add extra check for directory FIXME
    os.chdir("..")
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Motorola
  #-------------------------------------------------------------------------------
  elif (VENDOR == "motorola"):
    os.mkdir(SUB_SUB_TMP)
    at_unzip(IMAGE, None, SUB_SUB_TMP)
    os.chdir(SUB_SUB_TMP)
    # Need to add extra check for directory FIXME
    os.chdir("..")
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Nextbit
  #-------------------------------------------------------------------------------
  elif (VENDOR == "nextbit"):
    os.mkdir(SUB_SUB_TMP)
    at_unzip(IMAGE, None, SUB_SUB_TMP)
    os.chdir(SUB_SUB_TMP)
    os.rmdir("_MACOSX")
    # Need to add extra check for directory FIXME
    os.chdir("..")
  
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS LG
  #-------------------------------------------------------------------------------
  elif (VENDOR == "lg"):
    DECSUFFIX = IMAGE[-4:]
    # there is a chance that KDZ will fail
    if (DECSUFFIX == ".kdz"):
      os.mkdir(SUB_SUB_TMP)
      subprocess.run(["UNKDZ", "-f", IMAGE, "-o", SUB_SUB_TMP, "-x"])
      word_count = len(subprocess.run(["ls", SUB_SUB_TMP, "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
      if (word_count > 1):
        os.remove(SUB_SUB_TMP + "/" + ".kdz.params")
        DZFILE = subprocess.run(["ls", SUB_SUB_TMP + "/*.dz"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        # the other partitions with more than one chunk don't get combined into image
        SYSCOUNT = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "system_", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        USDCOUNT = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "userdata_", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        CCHCOUNT = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "cache_", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        CSTCOUNT = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "cust_", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        SYSNUM = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "system_", "|", "head", "-1", "|", "cut", "-d\'/\'", "-f", "1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        USDNUM = subprocess.run([UNDZ, "-f", DZFILE, "-l", "|", "grep", "userdata_", "|",  "head", "-1", "|", "cut", "-d\'/\'", "-f", "1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        CCHNUM = subprocess.run([undz, "-f", dzfile, "-l", "|", "grep", "cache_", "|", "head", "-1", "|", "cut", "-d\'/\'", "-f", "1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        # cust may be either singular or multiple; both cases are handled
        CSTNUM = subprocess.run([undz, "-f", dzfile, "-l", "|", "grep", "cust_", "|", "head", "-1", "|", "cut", "-d\'/\'", "-f", "1"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        PREDZ = int(subprocess.run(["ls", SUB_SUB_TMP, "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
        subprocess.run([UNDZ, "-f", DZFILE, "-o", SUB_SUB_TMP, "-c"])
        if (word_count != PREDZ):
          if (SYSCOUNT != 0):
            os.remove(SUB_SUB_TMP + "/"+ "system*.bin")
            subprocess.run([UNDZ, "-f", DZFILE, "-o", SUB_SUB_TMP, "-s", SYSNUM])
            os.remove(SUB_SUB_TMP + "/"+ "system.image.params")
          if (USDCOUNT != 0):
            os.remove(SUB_SUB_TMP + "/"+ "userdata*.bin")
            subprocess.run([UNDZ, "-f", DZFILE, "-o", SUB_SUB_TMP, "-s", USDNUM])
            os.remove(SUB_SUB_TMP + "/"+ "userdata.image.params")
          if (CCHCOUNT != 0):
            os.remove(SUB_SUB_TMP + "/"+ "cache*.bin")
            subprocess.run([UNDZ, "-f", DZFILE, "-o", SUB_SUB_TMP, "-s", CCHNUM])
            os.remove(SUB_SUB_TMP + "/"+ "cache.image.params")
          if (CSTCOUNT != 0):
            os.remove(SUB_SUB_TMP + "/"+ "cust*.bin")
            subprocess.run([UNDZ, "-f", DZFILE, "-o", SUB_SUB_TMP, "-s", CSTNUM])
            os.remove(SUB_SUB_TMP + "/"+ "cust.image.params")
          os.remove(DZFILE)
          os.remove(SUB_SUB_TMP+"/.dz.params")
        else:
          print("DZ extraction failed for: " + IMAGE, file=open(KDZ_LOG))
      else:
        print("DZ extraction failed for: " + IMAGE, file=open(KDZ_LOG))
    elif (DECSUFFIX == ".zip"):
      os.mkdir(SUB_SUB_TMP)
      at_unzip(IMAGE, None, SUB_SUB_TMP)
      # TODO: none of the current images we collected are of tot format
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Huawei or OnePlus or OPPO or Lineage
  #-------------------------------------------------------------------------------
  elif (VENDOR == "huawei") or (VENDOR == "oneplus") or (VENDOR == "oppo") or (VENDOR == "lineage"):
    os.mkdir(SUB_SUB_TMP)
    at_unzip(IMAGE, None, SUB_SUB_TMP)
    os.chdir(SUB_SUB_TMP)
    word_count = len(subprocess.run(["ls", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
    if (word_count == 1):
      EXTRA_SUB = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      subprocess.run(["cp", "-r", EXTRA_SUB, "."])
      os.rmdir(EXTRA_SUB)
    os.chdir("..")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS HTC
  #-------------------------------------------------------------------------------
  elif (VENDOR == "htc"):
    DECSUFFIX = IMAGE[-4:]
    if (DECSUFFIX == ".exe"):
      subprocess.run([HTCRUUDEC, "-sf", IMAGE])
      DECOUTPUT = subprocess.run(["ls", "|", "grep", str("OUT")], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      subprocess.run(["mv", DECOUTPUT, SUB_SUB_TMP])
    else:
      os.mkdir(SUB_SUB_TMP)
      at_unzip(IMAGE, SUB_SUB_TMP)
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Alcatel or BLU or VIVO or Xiaomi
  #-------------------------------------------------------------------------------
  elif (VENDOR == "alcatel") or (VENDOR == "blu") or (VENDOR == "vivo") or (VENDOR == "xiaomi"):
    at_unzip(IMAGE, None, None)
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS ASUS
  #-------------------------------------------------------------------------------
  elif (VENDOR == "asus"):
    os.mkdir(SUB_SUB_TMP)
    at_unzip(IMAGE, None, SUB_SUB_TMP)
    os.chdir(SUB_SUB_TMP)
    # single weird one-level nested case (ALL_HLOS.FILES.FASTBOOT)
    # but it may also be that there is a single zip or raw enclosed
    POTASUSZIP = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
    DECSUFFIX = POTASUSZIP[-4:]
    word_count = len(subprocess.run(["ls", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
    if (word_count == 1):
      if (DECSUFFIX == ".zip"):
        subprocess.run(["unzip", POTASUSZIP])
        os.remove(POTASUSZIP)
      elif (DECSUFFIX == ".raw"):
        print(IMAGE, file=open(RAW_LOG))
        # FIXME: need support for ASUS .raw format
        print("ERROR:  need support for ASUS .raw format")
        exit(0)
    elif (word_count == 2):
      POTASUSZIP = subprocess.run(["ls", ".zip"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      subprocess.run(["unzip", POTASUSZIP])
      os.remove(POTASUSZIP)
    word_count = len(subprocess.run(["ls", "|", "wc", "-l"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))
    if (word_count == 1):
      if (os.path.isdir(subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n"))):
        EXTRA_SUB = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
        subprocess.run(["cp", "-r", EXTRA_SUB, "."])
        os.rmdir(EXTRA_SUB)
      NSTAUSZIP = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
      subprocess.run(["unzip", NSTAUSZIP])
      os.remove(NSTAUSZIP)
    os.chdir("..")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS UNKOWN
  #-------------------------------------------------------------------------------
  else:
    VENDOR = "aosp"
    at_unzip(IMAGE, None, None)
  
  #####################################################################################################################
  #####################################################################################################################
  
  # Remove the raw image since we have decompressed it already
  if (AT_RES == "bad"):
    print ("Sorry, there is currently no support for decompressing this image!")
    exit(0)
  
  os.remove(IMAGE)

  # NOTE: assume there is only 1 dir after unziping
  SUB_SUB_DIR = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True).stdout.rstrip("\n")
  #MY_TMP = MY_TMP
  if (not os.path.isfile(MY_TMP)):
    open(MY_TMP, "w+")
    MY_TMP = os.getcwd() + "/" + MY_TMP
  if (not os.path.isfile(MY_USB)):
    open(MY_USB, "w+")
    MY_USB = os.getcwd() + "/" + MY_USB
  if (not os.path.isfile(MY_PROP)):
    open(MY_PROP, "w+")
    MY_PROP = os.getcwd() + "/" + MY_PROP
  MY_OUT = os.getcwd() + "/" + MY_OUT
  if (not os.path.isdir(SUB_SUB_DIR)):
    os.chdir(SUB_SUB_DIR)
  else:
    print("ERROR: More than 1 sub directory found!")
    exit(0)

  #####################################################################################################################
  #####################################################################################################################
  
  #################################
  # Final Processing and Handling #
  #################################

  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS AOSP
  #-------------------------------------------------------------------------------
  if (VENDOR == "aosp"):
    print("handling AOSP images...")
    
    # Check for another zip file inside and unzip it
    print("checking for more zips inside...")
    out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
    files = out.stdout.splitlines()
    for f in files:
      at_unzip(f, None, None)
      # Debug
      #print("$f at_unzip: $AT_RES"
      if (AT_RES == "good"):
        print("Unzipped sub image: " + f)
        # Remove the zip file
        os.remove(f)
    # Assume all the files will be flat in the same dir
    # without subdirs
    print("Extracting AT commands...")
    print("-------------------------")
    for f in files:
      process_file(f)
      print(f + " processed: " + AT_RES)
    print("-------------------------")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Samsung
  #-------------------------------------------------------------------------------
  elif (VENDOR == "samsung"):
    print("Handling Samsung images...")
    # After the unzip, we have 5 tar files, each of which needs to be extracted
    # in its own directory since they contain files with the same name...
    print("Unarchiving each zip inside...")
    out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
    files = out.stdout.splitlines()

    for f in files:
      print("Attempting to untar" + f)
      os.mkdir(TAR_TMP)
      at_unzip(f, None, TAR_TMP)
      if (AT_RES == "good"):
        print("Unzipped sub image: " + f)
        # Process files from the remote tar dir
        print("Extracting AT commands...")
        print("-------------------------")
        os.chdir(TAR_TMP)
        o = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
        sub_files = out.stdout.splitlines()
        for sub_f in sub_files:
          process_file(sub_f)
          print(sub_f + " processed: " + AT_RES)
        print("-------------------------")
      else:
        os.chdir(f)
        o = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
        sub_files = out.stdout.splitlines()
        for sub_f in sub_files:
          process_file(sub_f)
          print(sub_f + " processed: " + AT_RES)
        print("-------------------------")
      if (KEEPSTUFF == 1):
        subprocess.run(["cp","-r",TAR_TMP,MY_FULL_DIR+"/"+SUB_DIR+"/"+os.popen("basename \""+str(f)+"\"").read().rstrip("\n")])
      os.rmdir(TAR_TMP)
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Motorola
  #-------------------------------------------------------------------------------
  elif (VENDOR == "motorola"):
    print("Handling Motorola images...")
    # files may NOT be flat in the same directory without subdirectories
    print("Assuming no nested zips to handle... (or handled previously)")
    print("Extracting at commands...")
    print("-------------------------")
    
    out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
    files = out.stdout.splitlines()

    for f in files:
      process_file(f)
      print(f + " processed: " + AT_RES)
    print("-------------------------")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS Nextbit
  #-------------------------------------------------------------------------------
  elif (VENDOR == "nextbit"):
    print("Handling NextBit images...")
    # files may NOT be flat in the same directory without subdirectories
    print("Assuming no nested zips to handle... (or handled previously)")
    print("Extracting at commands...")
    print("-------------------------")
    
    out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
    files = out.stdout.splitlines()

    for f in files:
      process_file(f)
      print(f + " processed: " + AT_RES)
    print("-------------------------")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS LG
  #-------------------------------------------------------------------------------
  elif (VENDOR == "lg"):
    print("Handling LG images...")
    DECSUFFIX = IMAGE[-4:]
    if (DECSUFFIX == ".kdz"):
      print("Assuming no nested zips to handle... (or handled previously)")
      print("Extracting at commands...")
      print("-------------------------")
      
      out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
      files = out.stdout.splitlines()

      for f in files:
        process_file(f)
        print(f + " processed: " + AT_RES)
      print("-------------------------")
    elif (DECSUFFIX == ".zip"):
      # files will NOT be flat in the same directory without subdirectories
      print("Extracting at commands...")
      print("-------------------------")
      
      out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
      files = out.stdout.splitlines()

      for f in files:
        process_file(f)
        print(f + " processed: " + AT_RES)
      print("-------------------------")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS LG
  #-------------------------------------------------------------------------------
  elif (VENDOR == "htc"):
    print("Handling HTC images...")
    # Check for another zip file inside and unzip it
    print("Checking for more zips inside img zip...")
    out = subprocess.run(["ls"], universal_newlines=True, stdout=subprocess.PIPE, shell=True)
    files = out.stdout.splitlines()
    for f in files:
      at_unzip(f, None, None)
      # Debug
      #print("$f at_unzip: $AT_RES"
      if (AT_RES == "good"):
        print("Unzipped sub image: " + f)
        # Remove the zip file
        os.remove(f)
    # Assume all the files will not be flat in the same dir
    # without subdirs
    print("Extracting AT commands...")
    print("-------------------------")
    for f in files:
      process_file(f)
      print(f + " processed: " + AT_RES)
    print("-------------------------")
  #-------------------------------------------------------------------------------
  # IF THE VENDOR IS any other known
  #-------------------------------------------------------------------------------
  elif (VENDOR == "alcatel") or (VENDOR == "blu") or (VENDOR == "oneplus") or (VENDOR == "oppo") or (VENDOR == "xiaomi") or (VENDOR == "huawei") or (VENDOR == "lenovo") or (VENDOR == "sony") or (VENDOR == "vivo") or (VENDOR == "zte") or (VENDOR == "lineage") or (VENDOR == "asus"):
    print("Handling " + VENDOR + " images...")

    if (VENDOR == "huawei") or (VENDOR == "lenovo") or (VENDOR == "zte"):
      # UPDATE.APP in dload subdirectory; for now, assuming same filename across images
  		# ignoring cust_dload directory for now (accompanied by dload)
      if (os.path.isdir("dload")):
        os.chdir("dload")
        UPDATA(os.getcwd() + "/UPDATE.APP")
        os.remove("UPDATE.APP")
        os.chdir("..")
      if (os.path.isfile("UPDATE.APP")):
        UPDATA(os.getcwd() + "/UPDATE.APP")
        os.remove("UPDATE.APP")
      if (os.path.isfile("update.zip")):
        subprocess.run(["unzip", "update.zip"])
        os.remove("update.zip")
      if (os.path.isdir("Firmware") and os.path.isfile("Firmware/update.zip")):
        os.chdir("Firmware")
        subprocess.run(["unzip", "update.zip"])
        os.remove("UPDATE.APP")
        os.chdir("..")
    
    if (VENDOR == "sony"):
      if (os.path.isdir("Firmware") and os.path.isfile("Firmware/update.zip")):
        os.chdir("Firmware")
        subprocess.run(["unzip", "*.ftf"])
        os.remove("*.ftf")
        os.chdir("..")
  
      
    print("Extracting AT commands...")
    print("-------------------------")
    for f in files:
      process_file(f)
      print(f + " processed: " + AT_RES)
    print("-------------------------")

  #####################################################################################################################
  #####################################################################################################################
  
  #################################
  #        Findings summary       #
  #################################

  print("Summarizing the findings...")
  if (KEEPSTUFF == 0):
    os.rmdir(SUB_SUB_DIR)
  
  subprocess.run(["cat", MY_TMP], stdout=open(MY_OUT, "w+"))

#####################################################################################################################
##############################################################################################

#########################
#   Main Call    #
#########################

if __name__ == "__main__":
  main()

##############################################################################################
