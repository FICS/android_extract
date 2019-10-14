import os
import subprocess
import argparse

from subprocess import call

# Ported Python3 code from bash

# Original extraction tool found at https://github.com/FICS/atcmd/tree/master/extract


IMAGE="$1"
VENDOR="$2"
KEEPSTUFF="$4" # keep all the decompiled/unpackaged stuff for later analysis
VENDORMODE="$5" # should be provided as 0 unless alternate mode
EXTUSER="someuser" # TODO: replace with valid user to use keepstuff functionality
EXTGROUP="somegroup" # TODO: replace with valid group to use keepstuff functionality
MY_TMP="extract.sum"
MY_OUT="extract.db"
MY_USB="extract.usb"
MY_PROP="extract.prop"
#MY_TIZ="extract.tizen" # used to mark presence of tizen image(s), replaced by TIZ_LOG
TIZ_LOG="tizen.log" # samsung
PAC_LOG="spd_pac.log" # lenovo
SBF_LOG="sbf.log" # moto
MZF_LOG="mzf.log" # moto
RAW_LOG="raw.log" # asus
KDZ_LOG="kdz.log" # lg
MY_directory="extract/$2"
MY_FULL_directory="/data/atdb/extract/$2"
TOP_directory="extract"
#AT_CMD='AT\+|AT\*'
#AT_CMD='AT\+|AT\*|AT!|AT@|AT#|AT\$|AT%|AT\^|AT&' # expanding target AT Command symbols
#directory_TMP="$HOME/atsh_tmp$3"
#MNT_TMP="$HOME/atsh_tmp$3/mnt"
#APK_TMP="$HOME/atsh_apk$3"
#ZIP_TMP="$HOME/atsh_zip$3"
#ODEX_TMP="$HOME/atsh_odex$3"
#TAR_TMP="$HOME/atsh_tar$3"
#MSC_TMP="$HOME/atsh_msc$3"
#JAR_TMP="dex.jar"

##############################################################################################

DEPPATH=""
USINGDEPPATH=1 # 1 = true, 0 = false

DEX2JAR=$DEPPATH/dex2jar/dex-tools/target/dex2jar-2.1-SNAPSHOT/d2j-dex2jar.sh
JDCLI="$DEPPATH/jd-cmd/jd-cli/target/jd-cli.jar"
# These are the most recent versions of baksmali/smali that work with java 7 (needed for JADX-nohang)
BAKSMALI="$DEPPATH/baksmali-2.2b4.jar"
SMALI="$DEPPATH/smali-2.2b4.jar"
JADX=$DEPPATH/jadx/build/jadx/bin/jadx
# ~~~The following tools needed to unpack LG images: avail https://github.com/ehem/kdztools~~~
UNKDZ=$DEPPATH/kdztools/unkdz
UNDZ=$DEPPATH/kdztools/undz
UPDATA=$DEPPATH/split_updata.pl/splitupdate
UNSPARSE=$DEPPATH/combine_unsparse.sh
SDAT2IMG=$DEPPATH/sdat2img/sdat2img.py
SONYFLASH=$DEPPATH/flashtool/FlashToolConsole
SONYELF=$DEPPATH/unpackelf/unpackelf
IMGTOOL=$DEPPATH/imgtool/imgtool.ELF64
HTCRUUDEC=$DEPPATH/htcruu-decrypt3.6.5/RUU_Decrypt_Tool # rename libcurl.so to libcurl.so.4
SPLITQSB=$DEPPATH/split_qsb.pl
LESZB=$DEPPATH/szbtool/leszb # szb format1 for lenovo
UNYAFFS=$DEPPATH/unyaffs/unyaffs # yaffs2 format1 for sony

##############################################################################################

BOOT_OAT=""
BOOT_OAT_64=""
#AT_RES=""
SUB_SUB_TMP="extract_sub"
CHUNKED=0 # system.img
CHUNKEDO=0 # oem.img
CHUNKEDU=0 # userdata.img
COMBINED0=0 # system; may be a more elegant solution than this~
COMBINED1=0 # userdata
COMBINED2=0 # cache
COMBINED3=0 # factory or fac
COMBINED4=0 # preload
COMBINED5=0 # without_carrier_userdata
TARNESTED=0

##############################################################################################

#########################
#    Argument Parser    #
#########################

def parse_arguments():
  parser = argparse.ArgumentParser(description = 'Android image extraction tool.')
  parser.add_argument('-f', dest='filepath', metavar='FIRMWARE IMG FILEPATH', type=str,
    help = 'Path to the top-level packaged archive')
  parser.add_argument('-vender', dest='vender', metavar='VENDOR NAME', type=str,
    help = 'The vendor who produced the firmware image (e.g., Samsung, LG)')
  parser.add_argument('-i', dest='index', metavar='INDEX', type=int, 
    help = 'To extract multiple images at the same time, temporary directories will need different indices. For best results, supply an integer value > 0')
  parser.add_argument('-ks', dest='keepstuff', metavar='KEEP STUFF? [0 OR 1]',type=int, 
    help = 'if 0, will remove any extracted files after processing them;\nif 1, extracted files (e.g., filesystem contents, apps) will be kept')
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
  print("-ks <KEEP STUFF? [0 OR 1]>                 : to declare whether to remove extracted files after processing")
  print("--vendor-mode <VENDOR MODE [0 OR 1]>       : to configure specific vendor related settings")


##############################################################################################

#########################
#	   	  HELPERS			    #
#########################

def clean_up():
  call('sudo umount $MNT_TMP > /dev/null', shell=True)
  call('rm -rf $directory_TMP > /dev/null', shell=True)
  call('rm -rf $APK_TMP > /dev/null', shell=True)
  call('rm -rf $ZIP_TMP > /dev/null', shell=True)
  call('rm -rf $ODEX_TMP > /dev/null', shell=True)
  call('rm -rf $TAR_TMP > /dev/null', shell=True)
  call('rm -rf $MSC_TMP > /dev/null', shell=True)


# Decompress the zip-like file
# Return 'True' if the decompression is successful
# Otherwise 'False'
# NOTE: to support more decompressing methods, please add them here:

def at_unzip(filename, directory):
  # filename = "$1"
  # directory = "$2"
  format1 = filename[-3:] # format1 = 'file -b "$filename" | cut -d" " -f1'
  format2 = filename[-4:] # format2 = 'file -b "$filename" | cut -d" " -f2'

#  if [ "$format" == "zip" ] || [ "$format" == "ZIP" ] || [ "$format" == "Zip" ]; then
#    if [ -z "$dir" ]; then
#      unzip "$filename"
#    else
#      unzip -d "$dir" "$filename"
#    fi
#    AT_RES="good"
  if (format1 == "zip" ) or (format1 == "ZIP" ) or ( format1 == "Zip" ):
    if directory is None:     
      call('unzip ' + filename, shell=True)
    else:
      call('unzip -d ' + directory + ' ' + filename, shell=True)
    return True

#  elif [ "$format1" == "Java" ]; then
#    # mischaracterization of zip file as Java archive data for HTC
#    # or it is actually a JAR, but unzip works to extract contents
#    if [ -z "$directory" ]; then
#      unzip "$filename"
#    else
#      unzip -d "$directory" "$filename"
#    fi
#    AT_RES="good"
  elif (format2 == "Java"):
    # mischaracterization of zip file as Java archive data for HTC
    # or it is actually a JAR, but unzip works to extract contents
    if directory is None:     
      call('unzip ' + filename, shell=True)
    else:
      call('unzip -d ' + directory + ' ' + filename, shell=True)
    return True
    