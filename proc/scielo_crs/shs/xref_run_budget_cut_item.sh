. crossref_config.sh

AMOUNT_FILE=$1
CUT_FILE=$2
DEPOSIT_FILE=$3
PUBDATE=$4
PID=$5
INDIV_VALUE=$6

TOTAL_AVAILABLE=`cat $AMOUNT_FILE`

if [ "@$TOTAL_AVAILABLE" = "@0" ]
then
	echo "$PUBDATE $PID $INDIV_VALUE" >> $DEPOSIT_FILE
else
	$cisis_dir/mx null count=1 lw=999 "pft=if val('$TOTAL_AVAILABLE') - val('$INDIV_VALUE') >= 0 then f(val('$TOTAL_AVAILABLE')-val('$INDIV_VALUE'),1,2) else '0' fi" now > $AMOUNT_FILE
	echo "$PUBDATE $PID $INDIV_VALUE" >> $CUT_FILE
fi

