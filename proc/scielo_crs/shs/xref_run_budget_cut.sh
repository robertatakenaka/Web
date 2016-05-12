. crossref_config.sh

AMOUNT_FILE=$1
SRC_FILE=$2
CUT_FILE=$3
TODEPOSIT_FILE=$4

if [ -f $CUT_FILE ];
then
	rm $CUT_FILE
fi
if [ -f $TODEPOSIT_FILE ];
then
	rm $TODEPOSIT_FILE
fi

$cisis_dir/mx seq=$SRC_FILE lw=999 "pft='$conversor_dir/shs/xref_run_budget_cut_item.sh $AMOUNT_FILE $CUT_FILE $TODEPOSIT_FILE ',v1,' ',v2,' ',v3/" now > $MYTEMP/xref_run_budget_cut_item.sh
chmod 644 $MYTEMP/xref_run_budget_cut_item.sh
$MYTEMP/xref_run_budget_cut_item.sh
