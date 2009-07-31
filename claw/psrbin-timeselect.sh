#! /bin/bash
#
# Makes files with select statements for imaging a pulsar
#
######################
# customize here
#period=0.71452    # period from literature
#period=0.7136692   # period that fixes phase shift?
#bin=0.1
#phasebins=16
#outphases=1  # not yet implemented
#ints=3000
#t0h=02
#t0m=05
#t0s=02.4
#suffix='tst'
######################
period="$1"
binsize="$2"
phasebins="$3"
outphases="$4"
ints="$5"
t0h="$6"
t0m="$7"
t0s="$8"
suffix="$9"
timebins="${10}"
imagebin="${11}"

#set -e -x  # for debugging

# a guess at the number of pulses to interate over
numpulses=`echo 'scale=0;'${ints}'*'${binsize}'/'${period}'+ 1' | bc`  # original
timebinsize=`echo 'scale=1;'${ints}'*'${binsize}'/'${timebins} | bc`  # original

echo
echo '***Getting '${numpulses}' pulses assuming period '${period}'s***'
echo '***Averaging into '${timebins}' bins in time.  Data bin size is '${timebinsize}'s.***'  # to do:  multiple phases
echo

for ((j=0; j<=${timebins}-1; j++))   # iterate over pulse phase, zero based
do

outn='time-'${suffix}
file=${outn}'-time'${j}
fileavg=${outn}'-avg'${j}
fileoff=${outn}'-off'${j}
touch $file
touch $fileavg
touch $fileoff

istart=`echo 'scale=0;'${j}'*'${ints}'*'${binsize}'/('${timebins}'*'${period}')' | bc`
istop=`echo 'scale=0;('${j}'+1)*'${ints}'*'${binsize}'/('${timebins}'*'${period}')' | bc`

# repeat for average to subtract in each time bin
# get seconds offset
t1s=`echo 'scale=5; ('${t0s}' + '${period}' * '${istart}') ' | bc`
t2s=`echo 'scale=5; ('${t0s}' + '${period}' * '${istop}') ' | bc`

# adjust minutes offset
t1m=`echo 'scale=0; '${t1s}'/60' | bc`
t2m=`echo 'scale=0; '${t2s}'/60' | bc`
t1s=`echo 'scale=5; '${t1s}' - 60 * '${t1m} | bc`
t2s=`echo 'scale=5; '${t2s}' - 60 * '${t2m} | bc`

# adjust hour offset
t1h=`echo 'scale=0; '${t1m}'/60' | bc`
t2h=`echo 'scale=0; '${t2m}'/60' | bc`
t1m=`echo 'scale=5; '${t1m}' - 60 * '${t1h} | bc`
t2m=`echo 'scale=5; '${t2m}' - 60 * '${t2h} | bc`

# adjust minutes and second by origin
t1m=`echo 'scale=0; '${t0m}' + '${t1m} | bc`
t2m=`echo 'scale=0; '${t0m}' + '${t2m} | bc`
t1h=`echo 'scale=0; '${t0h}' + '${t1h} | bc`
t2h=`echo 'scale=0; '${t0h}' + '${t2h} | bc`

# initialize "previous" pulse end to start of observation
tph=`echo $t1h`
tpm=`echo $t1m`
tps=`echo $t1s`

# print average time filter to file
echo 'time('${t1h}':'${t1m}':'${t1s}','${t2h}':'${t2m}':'${t2s}')'  >> $fileavg

for ((i=${istart}; i<${istop}; i++))   # iterate over pulse number, 0-based
  do
  # get seconds offset
  t1s=`echo 'scale=5; ('${t0s}' + '${imagebin}' * '${period}' / ' ${phasebins} ' + '${period}' * '${i}') ' | bc`
  t2s=`echo 'scale=5; ('${t0s}' + ('${imagebin}' + 1) * '${period}' / ' ${phasebins} ' + '${period}' * '${i} ') ' | bc`

  # adjust minutes offset
  t1m=`echo 'scale=0; '${t1s}'/60' | bc`
  t2m=`echo 'scale=0; '${t2s}'/60' | bc`
  t1s=`echo 'scale=5; '${t1s}' - 60 * '${t1m} | bc`
  t2s=`echo 'scale=5; '${t2s}' - 60 * '${t2m} | bc`

  # adjust hour offset
  t1h=`echo 'scale=0; '${t1m}'/60' | bc`
  t2h=`echo 'scale=0; '${t2m}'/60' | bc`
  t1m=`echo 'scale=5; '${t1m}' - 60 * '${t1h} | bc`
  t2m=`echo 'scale=5; '${t2m}' - 60 * '${t2h} | bc`

  # adjust minutes and second by origin
  t1m=`echo 'scale=0; '${t0m}' + '${t1m} | bc`
  t2m=`echo 'scale=0; '${t0m}' + '${t2m} | bc`
  t1h=`echo 'scale=0; '${t0h}' + '${t1h} | bc`
  t2h=`echo 'scale=0; '${t0h}' + '${t2h} | bc`

  # print time filter to file
  echo 'time('${t1h}':'${t1m}':'${t1s}','${t2h}':'${t2m}':'${t2s}')'  >> $file
  echo 'time('${tph}':'${tpm}':'${tps}','${t1h}':'${t1m}':'${t1s}')'  >> $fileoff  # off pulse from previous to start of current
  tph=`echo $t2h`
  tpm=`echo $t2m`
  tps=`echo $t2s`
done

# check if file is over miriad select limit of 256 lines.  if so, split
numlines=`wc ${file} | gawk '{printf "%d \n", $0}' | head -n 1`
if [ $numlines -ge 256 ]
    then
    echo 'File too long.  Splitting.'
    split ${file} --lines=255 ${file}
    rm -f ${file}
else
    mv ${file} ${file}aa
    rm -f ${file}
fi

done
