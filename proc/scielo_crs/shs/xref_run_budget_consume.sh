. crossref_config.sh

# taxa para artigos recentes
PID=$1
FEE=$2
PRIOR=$3
BATCHBGID=$4

echo $FEE > $MYTEMP/doi_deposit_item_fee.text

$conversor_dir/shs/xref_run.sh $PID

if [ -f $MYTEMP/XREFWHATTODO ]
then
	rm $MYTEMP/XREFWHATTODO
fi
$cisis_dir/mx $XREF_DOI_REPORT btell=0 "bool=hr=$PID" "pft=if p(v30) then ,'done'/, fi" now > $MYTEMP/XREFWHATTODO
XREFWHATTODO=`cat $MYTEMP/XREFWHATTODO`

if [ "$XREFWHATTODO" == "done" ]
then
	if [ -f $MYTEMP/BILLSTATUS ]
	then
		rm $MYTEMP/BILLSTATUS
	fi
	$cisis_dir/mx cipar=$MYCIPFILE DB_BILL btell=0 "bool=$PID" "pft=v4/" now > $MYTEMP/BILLSTATUS
	BILLSTATUS=`cat $MYTEMP/BILLSTATUS`
	
	if [ ! "$BILLSTATUS" = "requested" ]			
	then
		$cisis_dir/mx $DB_BILL btell=0 "bool=$PID" count=1 "proc='d*'" copy=$DB_BILL now -all
		$cisis_dir/mx cipar=$MYCIPFILE null count=1 "proc=ref(['ARTIGO_DB']l(['ARTIGO_DB']'hr=$PID'),'a880{',v880,'{',|a881{|v881|{|,|a891{|v891|{|,|a223{|v223|{|,'a65{',v65,'{'),'a4{requested{a2{$FEE{a3{',date,'{a121{$PRIOR{a100{$BATCHBGID{a30{',ref(['XREF_DOI_REPORT']l(['XREF_DOI_REPORT']'hr=$PID'),v30,|^x|v930),'{'" append=$DB_BILL now -all
		$cisis_dir/mx $DB_BILL fst=@$conversor_dir/fst/bill.fst fullinv=$DB_BILL now -all
	fi

	$conversor_dir/shs/xref_run_budget_consume_item_fee.sh $MYTEMP/doi_deposit_item_fee.text
fi
