PID=$1
XMLPATH=$2
XMLFILE=$3
DOI=$4
AHEADPID=$5
AHEADXMLPATH=$6
AHEADXMLFILE=$7


if [ "@" == "@$AHEADPID"]
then
    # existe ahead e fasciculo
    if [ ! -f $XMLPATH/$XMLFILE && ! -f $AHEADXMLPATH/$AHEADXMLFILE ]
    then
        # pode ser feito deposito
        ./crossref_todolist_add_item.sh $AHEADPID $AHEADXMLPATH $AHEADXMLFILE $DOI 
    fi
else
    # existe somente fasciculo
    if [ ! -f $XMLPATH/$XMLFILE ]
    then
        # pode ser feito deposito
        ./crossref_todolist_add_item.sh $PID $XMLPATH $XMLFILE $DOI
    fi
fi
