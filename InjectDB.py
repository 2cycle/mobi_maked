[DB]
host=192.168.100.174
user=LTERNMS
passwd=LTERNMS123
db=NMS
charset=utf8
use_unicode=true

sql_insert =	insert into TB_SM_MF_HISTORY
                (
                CTRL_TIME,
                USER_ID,
                HOST_NAME,
				HOST_IP,
                SIOEF_NAME,
                SIOEF_PORT,
                GROUP_NAME,
                NODE_NAME,
                CTRL_TYPE,
                CTRL_CMD,
				CTRL_RESULT
                )
                VALUES(
                str_to_date('%s', '%%Y%%m%%d%%H%%i%%s'),
                '%s',
                '%s',
                '%s',
                '%s',
                %s,
                '%s',
                '%s',
                '%s',
				'%s',
				'%s'
                )
                ;

