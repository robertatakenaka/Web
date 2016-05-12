#
# This script is the main if there is a budget, otherwise the main script is the xref_run.sh
# This script accepts as parameters ORDER Descending or Ascending
# generates a list of articles sorted by publication date
# calculates the fee depending of the publication date according to the CrossRef policies
# then call xref_run.sh for each article
#

. crossref_config.sh
chmod 775 *.sh

BATCHBGID=`date`

# PREPARE THE ENVIROMENT
$conversor_dir/shs/xref_run_budget_prepare.sh

# saldo total
$cisis_dir/mx $DB_CTRL_BG tab=v9 now> $MYTEMP/doi_deposit_saldo_parcial1.seq
$conversor_dir/shs/xref_run_budget_sum.sh $MYTEMP/doi_deposit_saldo_parcial1 $MYTEMP/doi_deposit_saldo_parcial2
SALDO_TOTAL=`tail -n 1 $MYTEMP/doi_deposit_saldo_parcial2.seq`

# status atual
./xref_status_report_db.sh

# required budget
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "PID$ and not ( DEPOSIT_DATE=$ ) " tab=v12 now > $MYTEMP/doi_deposit_required_budget.seq
$conversor_dir/shs/xref_run_budget_sum.sh $MYTEMP/doi_deposit_required_budget $MYTEMP/doi_deposit_required_budget2
REQUIRED_BUDGET=`tail -n 1 $MYTEMP/doi_deposit_required_budget2.seq`

# list of deposit error
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "DEPOSIT_STATUS=error" "pft=v1/" now > $MYTEMP/doi_deposit_list_redeposit.txt
REDEPOSIT=`cat $MYTEMP/doi_deposit_list_redeposit.txt | wc -l`
echo >> $MYTEMP/doi_deposit_list_redeposit.txt
$cisis_dir/mx seq=$MYTEMP/doi_deposit_list_redeposit.txt lw=9999 "pft=if v1<>'' then |$conversor_dir/shs/xref_run.sh |v1/ fi" now > $MYTEMP/doi_deposit_xref_run.sh
chmod 644 $MYTEMP/doi_deposit_xref_run.sh

# list of never deposited
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "PID$ and not ( DEPOSIT_DATE=$ ) " lw=999 "pft=v2,'|',v1,'|',v12/" now | sort -r > $MYTEMP/doi_deposit_list_never_deposited.txt
cp $MYTEMP/doi_deposit_list_never_deposited.txt $MYTEMP/doi_deposit_list_to_deposit.txt
NEVERDEPOSIT=`cat $MYTEMP/doi_deposit_list_never_deposited.txt | wc -l`
echo >> $MYTEMP/doi_deposit_list_never_deposited.txt

# Filter the list, se necessário
$cisis_dir/mx null count=1 "pft=if val('$REQUIRED_BUDGET') > val('$SALDO_TOTAL') then f(val('$REQUIRED_BUDGET') - val('$SALDO_TOTAL'),1,2) fi" now > $MYTEMP/doi_deposit_amount_to_cut.txt

CUT_VALUE=`cat $MYTEMP/doi_deposit_amount_to_cut.txt`
if [ ! "@$CUT_VALUE" = "@" ];
then
	$conversor_dir/shs/xref_run_budget_cut.sh $MYTEMP/doi_deposit_amount_to_cut.txt $MYTEMP/doi_deposit_list_never_deposited.txt $MYTEMP/doi_deposit_list_cut.txt $MYTEMP/doi_deposit_list_to_deposit.txt 
fi

TODEPOSIT=`cat $MYTEMP/doi_deposit_list_to_deposit.txt | wc -l`
CUT=`cat $MYTEMP/doi_deposit_list_cut.txt | wc -l`

$cisis_dir/mx null count=1 "pft=if val('$REQUIRED_BUDGET') > val('$SALDO_TOTAL') then '$SALDO_TOTAL' else '$REQUIRED_BUDGET' ,fi" now > $MYTEMP/doi_deposit_list_used_budget.txt
USED=`cat $MYTEMP/doi_deposit_list_used_budget.txt`

$cisis_dir/mx seq=$MYTEMP/doi_deposit_list_to_deposit.txt lw=9999 "pft=if v2<>'' then $conversor_dir/shs/xref_run_budget_consume.sh ',v2,' ',v3,' ',mfn,' $BATCHBGID',,# fi" now > $MYTEMP/xref_run_budget_consume.sh
chmod 644 $MYTEMP/xref_run_budget_consume.sh



echo Procedimiento de DEPÓSITO DE DOI
echo 
echo VALOR PARA ARTICULOS DESDE DE     $FIRST_YEAR_OF_RECENT_FEE \$ $RECENT_FEE
echo VALOR PARA ARTICULOS ANTERIORES A $FIRST_YEAR_OF_RECENT_FEE \$ $BACKFILES_FEE
echo "Presupuesto disponible: $SALDO_TOTAL"
echo "Presupuesto necesario: $REQUIRED_BUDGET"
echo "Presupuesto usado en esta ejecución: $USED"
echo "Documentos para redepositar: $REDEPOSIT ($MYTEMP/xref_run.sh)"
echo "Documentos para depositar: $NEVERDEPOSIT "
echo "Documentos no processados: $CUT ($MYTEMP/doi_deposit_list_cut.txt)"
echo "Documentos processados: $TODEPOSIT ($MYTEMP/doi_deposit_list_never_deposited.txt)"
echo
echo ENTER para seguir o CTRL+C para interrumpir
read
clear

echo Redepositando ...
$MYTEMP/doi_deposit_xref_run.sh
echo Redeposito terminado
echo 

echo Depositando ...
$MYTEMP/xref_run_budget_consume.sh
echo Deposito terminado


$cisis_dir/mx null count=1 "proc='d2d90d121a100{$BATCHBGID{a121{$TODEPOSIT{a2{$USED{a90{',date,'{'" append=$DB_BATCH_RUN_BUDGET now -all
$cisis_dir/mx $DB_BATCH_RUN_BUDGET fst=@../fst/budget.fst fullinv=$DB_BATCH_RUN_BUDGET 

#$cisis_dir/mx $DB_BATCH_RUN_BUDGET btell=0 "bool=$BUDGETID" lw=9999  "pft=@$conversor_dir/pft/budget_report.pft" now

if [ ! -d ../output/crossref/report ]
then
	mkdir -p ../output/crossref/report/
fi

#$conversor_dir/shs/xref_report.sh $BUDGETID $BATCHBGID> ../output/crossref/report/$BUDGETID_$BATCHBGID.txt
#echo ===========  ATENCION ==================
#echo Lea el informe ../output/crossref/report/$BUDGETID_$BATCHBGID.txt
#echo fin
