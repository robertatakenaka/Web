#
# This script is the main if there is a budget, otherwise the main script is the xref_run.sh
# This script accepts as parameters ORDER Descending or Ascending
# generates a list of articles sorted by publication date
# calculates the fee depending of the publication date according to the CrossRef policies
# then call xref_run.sh for each article
#

. crossref_config.sh
chmod 775 *.sh

# PREPARE THE ENVIROMENT
$conversor_dir/shs/xref_run_budget_prepare.sh

# saldo total
$cisis_dir/mx $DB_CTRL_BG tab=v9 now> $MYTEMP/saldo_parcial1.seq
./xref_calculate_total.sh $MYTEMP/saldo_parcial1 $MYTEMP/saldo_parcial2
SALDO_TOTAL=`tail -n 1 $MYTEMP/saldo_parcial2.seq`

# status atual
./xref_status_report_db.sh

# required budget
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "PID$ and not ( DEPOSIT_DATE=$ ) " tab=v12 now > $MYTEMP/required_budget.seq
./xref_calculate_total.sh $MYTEMP/required_budget $MYTEMP/required_budget2
REQUIRED_BUDGET=`tail -n 1 $MYTEMP/required_budget2.seq`

# list of never deposited
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "PID$ and not ( DEPOSIT_DATE=$ ) " lw=999 "pft=v2,'|',v1,'|',v12/" now | sort > $MYTEMP/doi_deposit_list_never_deposited.txt
echo >> $MYTEMP/doi_deposit_list_never_deposited.txt
$cisis_dir/mx seq=$MYTEMP/doi_deposit_list_never_deposited.txt lw=9999 "pft=if v2<>'' and v3<>'' then './xref_run_budget_calculateFee.sh ',v2,' ',v3,#" now > $MYTEMP/xref_run_budget_calculateFee.sh
chmod 644 $MYTEMP/xref_run_budget_calculateFee.sh
NEVERDEPOSIT=`cat $MYTEMP/xref_run_budget_calculateFee.sh | wc -l`


# list of deposit error
$cisis_dir/mx btell=0 $XREF_DB_PATH/xref_status_report "DEPOSIT_STATUS=error" "pft=v1/" now > $MYTEMP/doi_deposit_list_redeposit.txt
echo >> $MYTEMP/doi_deposit_list_redeposit.txt
$cisis_dir/mx seq=$MYTEMP/doi_deposit_list_redeposit.txt lw=9999 "pft=if v1<>'' then |./xref_run.sh |v1,# fi" now > $MYTEMP/xref_run.sh
chmod 644 $MYTEMP/xref_run.sh
REDEPOSIT=`cat $MYTEMP/xref_run.sh | wc -l`

# 
$cisis_dir/mx null count=1 "pft=if val('$REQUIRED_BUDGET') <= val('$SALDO_TOTAL') then 'ok' else f(val('$REQUIRED_BUDGET')-val('$SALDO_TOTAL'),1,2) fi" now > $MYTEMP/budget_situation.txt


echo Procedimiento de DEPÓSITO DE DOI
echo 
echo VALOR PARA ARTICULOS DESDE DE     $FIRST_YEAR_OF_RECENT_FEE \$ $RECENT_FEE
echo VALOR PARA ARTICULOS ANTERIORES A $FIRST_YEAR_OF_RECENT_FEE \$ $BACKFILES_FEE
echo PARA EL PAGO SERA USADO EL PRESUPUESTO CUYO ID ES $BUDGETID
echo "Presupuesto disponible: $SALDO_TOTAL"
echo "Presupuesto necesario: $REQUIRED_BUDGET"
echo "Documentos para redepositar: $REDEPOSIT ($MYTEMP/xref_run.sh)"
echo "Documentos para depositar: $NEVERDEPOSIT ($MYTEMP/xref_run_budget_calculateFee.sh)"
echo
echo ENTER para seguir o CTRL+C para interrumpir
read
clear

echo Redepositando ...
$MYTEMP/xref_run.sh
echo Redeposito terminado
echo 

echo Depositando ...
$MYTEMP/xref_run_budget_calculateFee.sh
echo Deposito terminado


echo #######################
echo
echo   REPORT of BUDGET ID=$BUDGETID 
echo 
# $cisis_dir/mx cipar=$MYCIPFILE DB_BATCH_RUN_BUDGET btell=0 "bool=$BUDGETID" lw=9999  "pft=@$conversor_dir/pft/budget_report.pft" now

if [ ! -d ../output/crossref/report ]
then
	mkdir -p ../output/crossref/report/
fi
$conversor_dir/shs/xref_report.sh $BUDGETID $BATCHBGID> ../output/crossref/report/$BUDGETID_$BATCHBGID.txt
echo ===========  ATENCION ==================
echo Lea el informe ../output/crossref/report/$BUDGETID_$BATCHBGID.txt
echo fin
