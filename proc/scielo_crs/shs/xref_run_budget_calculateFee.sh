. crossref_config.sh

# taxa para artigos recentes
PID=$1
FEE=$2


if [ -f $MYTEMP/WHATTODO ]
then
	rm $MYTEMP/WHATTODO
fi


$cisis_dir/mx btell=0 $DB_CTRL_BG count=1 "bool=SALDO=$ and not ( SALDO=0 )" "pft=if val(v9) - val('$FEE') > 0 then fi" now 
$cisis_dir/mx cipar=$MYCIPFILE DB_PRESUPUESTOS btell=0 "bool=$BUDGETID" "pft=if val(v2)>=(val(ref(['DB_CTRL_BG']l(['DB_CTRL_BG']'$BUDGETID'),v2)) + val('$FEE')) then 'doit' else 'dont' fi/" now > $MYTEMP/WHATTODO

