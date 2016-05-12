. crossref_config.sh

. $conversor_dir/shs/xref_prepareEnv.sh

$cisis_dir/mx "seq=db_presupuestos.txt " create=$DB_PRESUPUESTOS  now -all
$cisis_dir/mx $DB_PRESUPUESTOS fst=@$conversor_dir/fst/budget.fst fullinv=$DB_PRESUPUESTOS 

d=`dirname $DB_CTRL_BG.mst`
if [ ! -d $d ]
then
	mkdir -p $d
fi

if [ -f $DB_BILL.mst ]
then
    # remove registros vazios
	$cisis_dir/mx null count=0 create=$MYTEMP/tempdb now -all
	$cisis_dir/mx $DB_BILL append=$MYTEMP/tempdb now -all
	$cisis_dir/mx $MYTEMP/tempdb create=$DB_BILL now -all
else
	# cria primeiro registro de $DB_BILL
	$cisis_dir/mx null count=1 "proc='a95{',date,'{'" create=$DB_BILL now -all
fi
$cisis_dir/mx $DB_BILL fst=@$conversor_dir/fst/bill.fst fullinv=$DB_BILL 

if [ -f $DB_CTRL_BG.mst ]
then
    # cria novos registros em db budget control
	$cisis_dir/mx null count=0 create=$MYTEMP/tempdb now -all
	$cisis_dir/mx $DB_PRESUPUESTOS btell=0 "proc='a1000{',ref(['$DB_CTRL_BG']l(['$DB_CTRL_BG']v1),v2),'{'" "proc=if v1000='' then 'd2d9a2{0{a9{',v2,'{' else 'd*' fi" append=$MYTEMP/tempdb now -all
	$cisis_dir/mx $MYTEMP/tempdb append=$DB_CTRL_BG  now -all

    # atualiza saldos, se necessario, ou seja, se nao existe o campo saldo
	$cisis_dir/mx btell=0 $DB_CTRL_BG "bool=$ and not ( SALDO=$ )" "proc='d1000a1000{',ref(['$DB_PRESUPUESTOS']l(['$DB_PRESUPUESTOS']v1),v2),'{'" "proc='d9a9{',f(val(v1000)-val(v2),1,2),'{'" copy=$DB_CTRL_BG now -all
else
	$cisis_dir/mx $DB_PRESUPUESTOS "proc='d2d9a2{0{a9{',v2,'{'" append=$DB_CTRL_BG now -all
fi
$cisis_dir/mx $DB_CTRL_BG fst=@$conversor_dir/fst/budget.fst fullinv=$DB_CTRL_BG 
