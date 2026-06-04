#include "driverlib.h"
#include "device.h"
#include "board.h"
#include "scicomm.h"
#include "math.h"


#define TAM_BUFFER_DAC 200
#define TAM_BUFFER_ADC 100

volatile Protocol_Header_t g_prot_header = {CMD_NONE, 0};

// Buffers do tamanho correto
uint16_t dac_buffer[TAM_BUFFER_DAC];
volatile uint16_t adc_buffer[TAM_BUFFER_ADC];
volatile float gain = 1.0f;
volatile uint16_t g_cnt_adc = 0;

// Avisa o compilador das interrupções
__interrupt void INT_SCI0_RX_ISR(void);
__interrupt void INT_ADC0_1_ISR(void);
__interrupt void INT_myCPUTIMER1_ISR(void);

void main(void)
{
    Device_init();
    Interrupt_initModule();
    Interrupt_initVectorTable();
    Board_init();

    // Mantemos o registro manual da SCI para evitar a tempestade de interrupções
    Interrupt_register(INT_SCIA_RX, &INT_SCI0_RX_ISR);
    Interrupt_enable(INT_SCIA_RX);

    // Zera os buffers
    int i;
    for(i = 0; i < TAM_BUFFER_DAC; i++) dac_buffer[i] = 0;
    for(i = 0; i < TAM_BUFFER_ADC; i++) adc_buffer[i] = 0;

    EINT;
    ERTM;

    while (1)
    {
        if (g_prot_header.cmd != CMD_NONE)
        {
            SCI_Command_e comando = g_prot_header.cmd;
            g_prot_header.cmd = CMD_NONE;

            if (comando == CMD_RECEIVE_ARRAY)
            {
                // Recebe os 200 pontos gerados no Python para o DAC
                protocolReceiveArray(SCI0_BASE, dac_buffer, TAM_BUFFER_DAC);
            }
            else if (comando == CMD_SEND_ARRAY)
            {
                uint16_t temp_buffer[TAM_BUFFER_ADC];
                int i;

                DINT;
                uint16_t snapshot_adc = g_cnt_adc;
                EINT;

                for(i = 0; i < TAM_BUFFER_ADC; i++)
                {
                    temp_buffer[i] = adc_buffer[(snapshot_adc + 1 + i) % TAM_BUFFER_ADC];
                }
                protocolSendArray(SCI0_BASE, temp_buffer, TAM_BUFFER_ADC);
            }

            SCI_clearInterruptStatus(SCI0_BASE, SCI_INT_RXFF);
            SCI_enableInterrupt(SCI0_BASE, SCI_INT_RXFF); 
        }
    }
}

// ==========================================================
// ISRs (Interrupções)
// ==========================================================

// ISR da SCI 
__interrupt void INT_SCI0_RX_ISR(void)
{
    uint16_t header[PROTOCOL_HEADER_SIZE];

    SCI_readCharArray(SCI0_BASE, header, PROTOCOL_HEADER_SIZE);
    
    g_prot_header.cmd = (SCI_Command_e)header[0];
    g_prot_header.data_len = header[1] | (header[2] << 8);
    
    SCI_disableInterrupt(SCI0_BASE, SCI_INT_RXFF);
    SCI_clearInterruptStatus(SCI0_BASE, SCI_INT_RXFF);
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}

// ISR do ADC 
__interrupt void INT_ADC0_1_ISR(void)
{
    g_cnt_adc = (g_cnt_adc + 1) % TAM_BUFFER_ADC;
    adc_buffer[g_cnt_adc] = ADC_readResult(ADC0_RESULT_BASE, ADC0_SOC0);
    
    ADC_clearInterruptStatus(ADC0_BASE, ADC_INT_NUMBER1);
    Interrupt_clearACKGroup(INT_ADC0_1_INTERRUPT_ACK_GROUP);
}

// ISR do Timer / DAC 
__interrupt void INT_myCPUTIMER1_ISR(void)
{
    static uint16_t cnt_dac = 0;
    
    DAC_setShadowValue(DAC0_BASE, (uint16_t)(gain * dac_buffer[cnt_dac]));
    cnt_dac = (cnt_dac + 1) % TAM_BUFFER_DAC;
}