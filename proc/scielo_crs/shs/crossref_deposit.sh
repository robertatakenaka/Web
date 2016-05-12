PID=$1
XMLPATH=$2
XMLFILE=$3

echo $PID >> toDoList.txt
mkdir -p $conversor_dir/output/crossref/$XMLPATH
$JAVA_HOME/bin/java -Dfile.encoding=ISO-8859-1 -cp .:$conversor_dir/java/crossrefSubmit.jar:$conversor_dir/java/lib/HTTPClient.jar org.crossref.doUpload $crossrefUserName $crossrefPassword $conversor_dir/output/crossref/$XMLPATH/$XMLFILE $PID $logDate >> crossref_UploadXML.sh

     
