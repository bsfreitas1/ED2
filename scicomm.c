/*
 * scicomm.c
 *
 * Created on: 13 de jun de 2025
 * Author: Guilherme Márcio Soares
 */
#include "board.h"
#include "device.h"
#include "scicomm.h"

int protocolReceiveInt(unsigned int sci_base)
{
    uint16_t buffer[INT_SIZE];
    SCI_readCharArray(sci_base, buffer, INT_SIZE);
    return (buffer[0] | (buffer[1] << 8U));
}

void protocolSendInt(unsigned int sci_base, int data)
{
    uint16_t txBuf[INT_SIZE];
    txBuf[0] = (uint16_t)(data & 0x00FF);
    txBuf[1] = (uint16_t)((data >> 8U) & 0x00FF);

    SCI_writeCharArray(sci_base, txBuf, INT_SIZE);
}

// ==========================================================
// NOVAS FUNÇÕES: IMPLEMENTAÇÃO PARA VETORES
// ==========================================================

void protocolReceiveArray(unsigned int sci_base, uint16_t *buffer, uint16_t length)
{
    uint16_t rxBuf[INT_SIZE];
    uint16_t i;
    
    for(i = 0; i < length; i++)
    {
        // Lê 2 bytes correspondentes a 1 inteiro de 16 bits
        SCI_readCharArray(sci_base, rxBuf, INT_SIZE);
        
        // Reconstrói o valor e salva na posição i do buffer
        buffer[i] = (rxBuf[0] | (rxBuf[1] << 8U));
    }
}

void protocolSendArray(unsigned int sci_base, uint16_t *buffer, uint16_t length)
{
    uint16_t txBuf[INT_SIZE];
    uint16_t i;
    
    for(i = 0; i < length; i++)
    {
        // Quebra o valor de 16 bits em 2 bytes de 8 bits
        txBuf[0] = (uint16_t)(buffer[i] & 0x00FF);
        txBuf[1] = (uint16_t)((buffer[i] >> 8U) & 0x00FF);
        
        // Envia os 2 bytes
        SCI_writeCharArray(sci_base, txBuf, INT_SIZE);
    }
}