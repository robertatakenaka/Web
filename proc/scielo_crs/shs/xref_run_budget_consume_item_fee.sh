. crossref_config.sh

REMAINDER_FILE=$1

VALUE_TO_USE=`cat $REMAINDER_FILE`

if [ ! "@$VALUE_TO_USE" = "@0" ]
then

	$cisis_dir/mx $DB_CTRL_BG btell=0 count=1 "bool=SALDO=$ and not ( SALDO=0 )" "pft=v9/" now > $MYTEMP/doi_deposit_avail_now.txt
	AVAIL=`cat $MYTEMP/doi_deposit_avail_now.txt`

	$cisis_dir/mx null count=1 lw=999 "pft=f(val('$AVAIL') - val('$VALUE_TO_USE'),1,2)" now > $MYTEMP/doi_deposit_diff.txt
	DIFF=`cat $MYTEMP/doi_deposit_diff.txt`

	$cisis_dir/mx null count=1 lw=999 "pft=if val('$DIFF') > 0 then '0' else f(val('$VALUE_TO_USE')-val('$AVAIL'),1,2) fi" now > $REMAINDER_FILE

	$cisis_dir/mx $DB_CTRL_BG btell=0 "bool=SALDO=$ and not ( SALDO=0 )" "proc='d2d90d9a2{',f(val(v2)+val('$FEE')-val('$DIFF'),1,2),'{a9{',f(val(v9)-val('$FEE')+val('$DIFF'),1,2),'{a90{',date,'{'" copy=$DB_CTRL_BG now -all
	$cisis_dir/mx $DB_CTRL_BG fst=@$conversor_dir/fst/budget.fst copy=$DB_CTRL_BG now -all

	$conversor_dir/shs/xref_run_budget_consume_item_fee.sh $REMAINDER_FILE
fi

