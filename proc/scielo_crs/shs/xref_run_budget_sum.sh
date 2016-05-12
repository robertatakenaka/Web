
TABULATED=$1
PARTIAL_SUM=$2

. crossref_config.sh


$cisis_dir/mx seq=$TABULATED.seq "pft=f(val(v3)*val(v2),1,2)/" now> $PARTIAL_SUM.seq
$cisis_dir/mx seq=$PARTIAL_SUM.seq create=$PARTIAL_SUM now -all

$cisis_dir/mx $PARTIAL_SUM "proc='a9{',if mfn = 1 then v1 else f(val(ref(mfn-1,v9))+val(v1),1,2) fi,'{'" copy=$PARTIAL_SUM now -all
$cisis_dir/mx $PARTIAL_SUM "pft=v9/" now > $PARTIAL_SUM.seq

#SALDO_TOTAL=`tail -n 1 $PARTIAL_SUM.seq`
