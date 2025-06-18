
PACKET_ID_SESSION_ATTRIBUTE = "packetID"
PACKET_SESSION_ATTRIBUTE = "egtspacket"
RESEND_ATTEMPT_NUMBER_ATTRIBUTE = "resentattemptnumber"
RECORD_ID_SESSION_ATTRIBUTE = "recordID"
IMEI_LEAD_SIMBOL = "E"
AUTHORIZED = "egtsauthorized"

DEFAULT_CHARSET = "CP1251"
DEFAULT_BEGIN_TIME = 1262304000  # 1 jan 2010 0:0:0:000
BASE_DIGITAL_PASS_SENSORS_ADDRESS = 1000
BASE_DIGITAL_DUT_ADDRESS = 1020
PACKET_HEADER_VERSION = 1
PACKET_HEADER_PREFIX = 0
PACKET_HEADER_FIRST_SIZE = 4
PACKET_HEADER_SECOND_SIZE = 6
PACKET_HEADER_THIRD_SIZE = 5
ROUTE_HEADER_TRANSPORT_SIZE = 16
HEADER_TRANSPORT_SIZE = 11
EGTS_PT_RESPONSE = 0  # подтверждение на пакет Транспортного уровня
EGTS_PT_APPDATA = 1  # пакет, содержащий данные протокола Уровня поддержки услуг
EGTS_PT_SIGNED_APPDATA = 2  # пакет, содержащий данные протокола Уровня поддержки услуг с цифровой подписью
EGTS_PC_OK = 0  # успешно обработано
EGTS_PC_IN_PROGRESS = 1  # в процессе обработки
EGTS_PC_UNS_PROTOCOL = 128  # неподдерживаемый протокол
EGTS_PC_DECRYPT_ERROR = 129  # ошибка декодирования
EGTS_PC_PROC_DENIED = 130  # обработка запрещена
EGTS_PC_INC_HEADERFORM = 131  # неверный формат заголовка
EGTS_PC_INC_DATAFORM = 132  # неверный формат данных
EGTS_PC_UNS_TYPE = 133  # неподдерживаемый тип
EGTS_PC_NOTEN_PARAMS = 134  # неверное количество параметров
EGTS_PC_DBL_PROC = 135  # попытка повторной обработки
EGTS_PC_PROC_SRC_DENIED = 136  # обработка данных от источника запрещена
EGTS_PC_HEADERCRC_ERROR = 137  # ошибка контрольной суммы заголовка
EGTS_PC_DATACRC_ERROR = 138  # ошибка контрольной суммы данных
EGTS_PC_INVDATALEN = 139  # некорректная длина данных
EGTS_PC_ROUTE_NFOUND = 140  # маршрут не найден
EGTS_PC_ROUTE_CLOSED = 141  # маршрут закрыт
EGTS_PC_ROUTE_DENIED = 142  # маршрутизация запрещена
EGTS_PC_INVADDR = 143  # неверный адрес
EGTS_PC_TTLEXPIRED = 144  # превышено количество ретрансляции данных
EGTS_PC_NO_ACK = 145  # нет подтверждения
EGTS_PC_OBJ_NFOUND = 146  # объект не найден
EGTS_PC_EVNT_NFOUND = 147  # событие не найдено
EGTS_PC_SRVC_NFOUND = 148  # сервис не найден
EGTS_PC_SRVC_DENIED = 149  # сервис запрещен
EGTS_PC_SRVC_UNKN = 150  # неизвестный тип сервиса
EGTS_PC_AUTH_DENIED = 151  # авторизация запрещена
EGTS_PC_ALREADY_EXISTS = 152  # объект уже существует
EGTS_PC_ID_NFOUND = 153  # идентификатор не найден
EGTS_PC_INC_DATETIME = 154  # неправильная дата и время
EGTS_PC_IO_ERROR = 155  # ошибка ввода/вывода
EGTS_PC_NO_RES_AVAIL = 156  # недостаточно ресурсов
EGTS_PC_MODULE_FAULT = 157  # внутренний сбой модуля
EGTS_PC_MODULE_PWR_FLT = 158  # сбой в работе цепи питания модуля
EGTS_PC_MODULE_PROC_FLT = 159  # сбой в работе микроконтроллера модуля
EGTS_PC_MODULE_SW_FLT = 160  # сбой в работе программы модуля
EGTS_PC_MODULE_FW_FLT = 161  # сбой в работе внутреннего ПО модуля
EGTS_PC_MODULE_IO_FLT = 162  # сбой в работе блока ввода/вывода модуля
EGTS_PC_MODULE_MEM_FLT = 163  # сбой в работе внутренней памяти модуля
EGTS_PC_TEST_FAILED = 164  # тест не пройден
EGTS_SR_RECORD_RESPONSE = 0  # Подзапись применяется для осуществления подтверждения процесса обработки записи ППУ. Данный тип подзаписи должен поддерживаться всеми Сервисами.

EGTS_AUTH_SERVICE = 1
# ======================================================
EGTS_SR_TERM_IDENTITY = 1  # Подзапись используется АС при запросе авторизации на ТП и содержит учётные данные АС
EGTS_SR_DISPATCHER_IDENTITY = 5  # Подзапись используется ТП при запросе авторизации на ТП и содержит учётные данные ТП
EGTS_SR_MODULE_DATA = 2  # Подзапись предназначена для передачи на ТП информации об инфраструктуре на стороне АС, о составе, состоянии и параметрах блоков и модулей АС. Данная подзапись является опциональной и разработчик АС сам принимает решение о необходимости заполнения  полей и отправки подзаписи. Одна подзапись описывает один модуль. В одной записи может передаваться последовательно несколько таких подзаписей, что позволяет передать данные об отдельных составляющих всей аппаратной части АС и периферийного оборудования
EGTS_SR_VEHICLE_DATA = 3  # Подзапись применяется АС для передачи на ТП информации о транспортном средстве.
EGTS_SR_AUTH_PARAMS = 6  # Подзапись используется ТП для передачи на АТ данных о способе и параметрах шифрования,  требуемого для дальнейшего взаимодействия
EGTS_SR_AUTH_INFO = 7  # Подзапись предназначена для передачи на ТП аутентификационных данных АС с использованием ранее переданных со стороны ТП параметров для осуществления шифрования данных.
EGTS_SR_SERVICE_INFO = 8  # Данный тип подзаписи используется для информирования принимающей стороны, АС или ТП, в зависимости от направления отправки, о поддерживаемых Сервисах, а также для запроса определённого набора требуемых Сервисов (от АС к ТП)
EGTS_SR_RESULT_CODE = 9  # Подзапись применяется ТП для информирования АС о результатах процедуры аутентификации АС.
# ======================================================
EGTS_TELEDATA_SERVICE = 2
# ======================================================
# Используется абонентским терминалом при передаче основных данных определения местоположения
EGTS_SR_POS_DATA = 16
# Используется абонентским терминалом при передаче дополнительных данных определения местоположения
EGTS_SR_EXT_POS_DATA = 17
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс   информации о    состоянии дополнительных дискретных и  аналоговых входов
EGTS_SR_AD_SENSORS_DATA = 18
# Используется аппаратно-программным комплексом для передачи на абонентский терминал данных  о значении  счетных входов
EGTS_SR_COUNTERS_DATA = 19
# Используется для передачи на аппаратно-программный комплекс информации о  состоянии абонентского терминала
EGTS_SR_STATE_DATA = 21
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс данных о  состоянии шлейфовых входов
EGTS_SR_LOOPIN_DATA = 22
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс  данных о  состоянии одного дискретного входа
EGTS_SR_ABS_DIG_SENS_DATA = 23
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс  данных о  состоянии одного аналогового входа
EGTS_SR_ABS_AN_SENS_DATA = 24
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс  данных о  состоянии одного счетного входа
EGTS_SR_ABS_CNTR_DATA = 25
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс  данных о  состоянии одного шлейфового входа
EGTS_SR_ABS_LOOPIN_DATA = 26
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс данных о показаниях ДУЖ
EGTS_SR_LIQUID_LEVEL_SENSOR = 27
# Применяется абонентским терминалом для передачи на аппаратно-программный комплекс данных о показаниях счетчиков пассажиропотока
EGTS_SR_PASSENGERS_COUNTERS = 28

EGTS_SR_TEST_ID_DATA = 29
# ======================================================
EGTS_COMMANDS_SERVICE = 4
# ======================================================
EGTS_SR_COMMAND_DATA = 51  # Подзапись используется АС и ТП для передачи команд, информационных сообщений, подтверждений доставки, подтверждений выполнения команд, подтверждения прочтения сообщений.
# ======================================================
EGTS_FIRMWARE_SERVICE = 9
# ======================================================
EGTS_SR_SERVICE_PART_DATA = 33  # Подзапись предназначена для передачи на АС данных, которые разбиваются на части и передаются последовательно. Данная подзапись применяется для передачи больших объектов, длина которых не позволяет передать их на АС одним пакетом.
EGTS_SR_SERVICE_FULL_DATA = 34  # Подзапись предназначена для передачи на АС данных, которые не разбиваются на части, а передаются одним пакетом.
# ======================================================
EGTS_ECALL_SERVICE = 10
# ======================================================
EGTS_SR_ACCEL_DATA = 20  # Подзапись предназначена для передачи на ТП данных профиля ускорения АС
EGTS_SR_MSD_DATA = 50  # Подзапись используется АС для передачи МНД на ТП.
# ======================================================
EGTS_RECORD_RESPONSE = 11
# ======================================================
PREFIX_MASK = 0xC0
ROUTE_MASK = 0x20
ENCRIPTION_ALGORITHM_MASK = 0x18
COMPRESSED_MASK = 0x04
PRIORITY_MASK = 0x03

SSOD = 0x80
RSOD = 0x40
GRP = 0x20
RPP = 0x18
TMFE = 0x04
EVFE = 0x02
OBFE = 0x01

BYTE_SIZE = 1
SHORT_SIZE = 2
INT_SIZE = 4
LONG_SIZE = 8


packet_types = {
    EGTS_PT_RESPONSE: 'EGTS_PT_RESPONSE',
    EGTS_PT_APPDATA: 'EGTS_PT_APPDATA',
    EGTS_PT_SIGNED_APPDATA: 'EGTS_PT_APPDATA'
}


service_types = {
    EGTS_AUTH_SERVICE: "EGTS_AUTH_SERVICE",
    EGTS_TELEDATA_SERVICE: "EGTS_TELEDATA_SERVICE",
    EGTS_COMMANDS_SERVICE: "EGTS_COMMANDS_SERVICE",
    EGTS_FIRMWARE_SERVICE: "EGTS_FIRMWARE_SERVICE",
    EGTS_ECALL_SERVICE: 'EGTS_ECALL_SERVICE',
    EGTS_RECORD_RESPONSE: 'EGTS_RECORD_RESPONSE'
}


sub_record_types = {
    EGTS_AUTH_SERVICE: {
        EGTS_SR_RECORD_RESPONSE: "EGTS_SR_RECORD_RESPONSE",
        EGTS_SR_TERM_IDENTITY: "EGTS_SR_TERM_IDENTITY",
        EGTS_SR_MODULE_DATA: "EGTS_SR_MODULE_DATA",
        EGTS_SR_VEHICLE_DATA: "EGTS_SR_VEHICLE_DATA",
        EGTS_SR_DISPATCHER_IDENTITY: "EGTS_SR_DISPATCHER_IDENTITY",
        EGTS_SR_AUTH_PARAMS: "EGTS_SR_AUTH_PARAMS",
        EGTS_SR_AUTH_INFO: "EGTS_SR_AUTH_INFO",
        EGTS_SR_SERVICE_INFO: "EGTS_SR_SERVICE_INFO",
        EGTS_SR_RESULT_CODE: "EGTS_SR_RESULT_CODE"
    },
    EGTS_TELEDATA_SERVICE: {
        EGTS_SR_RECORD_RESPONSE: "EGTS_SR_RECORD_RESPONSE",
        EGTS_SR_POS_DATA: "EGTS_SR_POS_DATA",
        EGTS_SR_EXT_POS_DATA: "EGTS_SR_EXT_POS_DATA",
        EGTS_SR_AD_SENSORS_DATA: "EGTS_SR_AD_SENSORS_DATA",
        EGTS_SR_COUNTERS_DATA: "EGTS_SR_COUNTERS_DATA",
        EGTS_SR_ACCEL_DATA: "EGTS_SR_ACCEL_DATA",
        EGTS_SR_STATE_DATA: "EGTS_SR_STATE_DATA",
        EGTS_SR_LOOPIN_DATA: "EGTS_SR_LOOPIN_DATA",
        EGTS_SR_ABS_DIG_SENS_DATA: "EGTS_SR_ABS_DIG_SENS_DATA",
        EGTS_SR_ABS_AN_SENS_DATA: "EGTS_SR_ABS_AN_SENS_DATA",
        EGTS_SR_ABS_CNTR_DATA: "EGTS_SR_ABS_CNTR_DATA",
        EGTS_SR_ABS_LOOPIN_DATA: "EGTS_SR_ABS_LOOPIN_DATA",
        EGTS_SR_LIQUID_LEVEL_SENSOR: "EGTS_SR_LIQUID_LEVEL_SENSOR",
        EGTS_SR_PASSENGERS_COUNTERS: "EGTS_SR_PASSENGERS_COUNTERS",
        EGTS_SR_TEST_ID_DATA: "EGTS_SR_TEST_ID_DATA"
    },
    EGTS_COMMANDS_SERVICE: {},
    EGTS_FIRMWARE_SERVICE: {},
    EGTS_ECALL_SERVICE: {}
}

response_types = {
    EGTS_PC_OK: 'EGTS_PC_OK',
    EGTS_PC_IN_PROGRESS: 'EGTS_PC_IN_PROGRESS',
    EGTS_PC_UNS_PROTOCOL: 'EGTS_PC_UNS_PROTOCOL',
    EGTS_PC_DECRYPT_ERROR: 'EGTS_PC_DECRYPT_ERROR',
    EGTS_PC_PROC_DENIED: 'EGTS_PC_PROC_DENIED',
    EGTS_PC_INC_HEADERFORM: 'EGTS_PC_INC_HEADERFORM',
    EGTS_PC_INC_DATAFORM: 'EGTS_PC_INC_DATAFORM',
    EGTS_PC_UNS_TYPE: 'EGTS_PC_UNS_TYPE',
    EGTS_PC_NOTEN_PARAMS: 'EGTS_PC_NOTEN_PARAMS',
    EGTS_PC_DBL_PROC: 'EGTS_PC_DBL_PROC',
    EGTS_PC_PROC_SRC_DENIED: 'EGTS_PC_PROC_SRC_DENIED',
    EGTS_PC_HEADERCRC_ERROR: 'EGTS_PC_HEADERCRC_ERROR',
    EGTS_PC_DATACRC_ERROR: 'EGTS_PC_DATACRC_ERROR',
    EGTS_PC_INVDATALEN: 'EGTS_PC_INVDATALEN',
    EGTS_PC_ROUTE_NFOUND: 'EGTS_PC_ROUTE_NFOUND',
    EGTS_PC_ROUTE_CLOSED: 'EGTS_PC_ROUTE_CLOSED',
    EGTS_PC_ROUTE_DENIED: 'EGTS_PC_ROUTE_DENIED',
    EGTS_PC_INVADDR: 'EGTS_PC_INVADDR',
    EGTS_PC_TTLEXPIRED: 'EGTS_PC_TTLEXPIRED',
    EGTS_PC_NO_ACK: 'EGTS_PC_NO_ACK',
    EGTS_PC_OBJ_NFOUND: 'EGTS_PC_OBJ_NFOUND',
    EGTS_PC_EVNT_NFOUND: 'EGTS_PC_EVNT_NFOUND',
    EGTS_PC_SRVC_NFOUND: 'EGTS_PC_SRVC_NFOUND',
    EGTS_PC_SRVC_DENIED: 'EGTS_PC_SRVC_DENIED',
    EGTS_PC_SRVC_UNKN: 'EGTS_PC_SRVC_UNKN',
    EGTS_PC_AUTH_DENIED: 'EGTS_PC_AUTH_DENIED',
    EGTS_PC_ALREADY_EXISTS: 'EGTS_PC_ALREADY_EXISTS',
    EGTS_PC_ID_NFOUND: 'EGTS_PC_ID_NFOUND',
    EGTS_PC_INC_DATETIME: 'EGTS_PC_INC_DATETIME',
    EGTS_PC_IO_ERROR: 'EGTS_PC_IO_ERROR',
    EGTS_PC_NO_RES_AVAIL: 'EGTS_PC_NO_RES_AVAIL',
    EGTS_PC_MODULE_FAULT: 'EGTS_PC_MODULE_FAULT',
    EGTS_PC_MODULE_PWR_FLT: 'EGTS_PC_MODULE_PWR_FLT',
    EGTS_PC_MODULE_PROC_FLT: 'EGTS_PC_MODULE_PROC_FLT',
    EGTS_PC_MODULE_SW_FLT: 'EGTS_PC_MODULE_SW_FLT',
    EGTS_PC_MODULE_FW_FLT: 'EGTS_PC_MODULE_FW_FLT',
    EGTS_PC_MODULE_IO_FLT: 'EGTS_PC_MODULE_IO_FLT',
    EGTS_PC_MODULE_MEM_FLT: 'EGTS_PC_MODULE_MEM_FLT',
    EGTS_PC_TEST_FAILED: 'EGTS_PC_TEST_FAILED'
}
