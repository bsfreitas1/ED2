import serial
import struct
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# --- CONFIGURACOES DE COMUNICACAO ---
SERIAL_PORT = 'COM8'  
BAUD_RATE = 115200

# --- CONFIGURACOES DE HARDWARE  ---
TAM_BUFFER_DAC = 200
TAM_BUFFER_ADC = 100

# Frequências de acordo com a temporização que foram configuradas no SysConfig / CPU Timer do  CCS.
FS_DAC = 10000  
FS_ADC = 5000  

# --- COMANDOS DO PROTOCOLO ---
CMD_RECEIVE_ARRAY = 3  # PC envia vetor para o DAC
CMD_SEND_ARRAY    = 4  # PC pede vetor do ADC


def enviar_vetor_dac(ser, sinal_uint16):
    """Empacota e envia o vetor de 200 pontos para o dac_buffer do C2000."""
    if len(sinal_uint16) != TAM_BUFFER_DAC:
        print(f"Erro: O vetor deve ter exatamente {TAM_BUFFER_DAC} pontos.")
        return False

    payload_size_bytes = TAM_BUFFER_DAC * 2
    header = struct.pack('<Bh', CMD_RECEIVE_ARRAY, payload_size_bytes)
    
    payload = struct.pack(f'<{TAM_BUFFER_DAC}H', *sinal_uint16)
    
    ser.write(header + payload)
    time.sleep(0.1)
    print("-> Vetor enviado com sucesso para o DAC do microcontrolador.")
    return True


def receber_vetor_adc(ser):
    """Solicita e recebe os 100 pontos capturados pelo adc_buffer"""
    ser.flushInput()  # Limpa o buffer de entrada 
    
    # Envia comando de solicitação
    request = struct.pack('<Bh', CMD_SEND_ARRAY, 0)
    ser.write(request)

    bytes_esperados = TAM_BUFFER_ADC * 2
    bytes_lidos = ser.read(bytes_esperados)
    
    if len(bytes_lidos) < bytes_esperados:
        print("Erro: Timeout ou falha na recepção dos dados do ADC.")
        return None
    
    # Desempacota os bytes recebidos de volta para um array numpy
    dados_adc = struct.unpack(f'<{TAM_BUFFER_ADC}H', bytes_lidos)
    return np.array(dados_adc, dtype=np.float64)


def plotar_sinal(dados_adc, titulo_teste):
    """Processa a FFT e plota os gráficos no domínio do tempo e da frequência"""
    # Vetor de tempo baseado na taxa de amostragem real do ADC
    tempo = np.arange(TAM_BUFFER_ADC) / FS_ADC
    
    # --- Processamento da FFT ---
    N = TAM_BUFFER_ADC
    yf = fft(dados_adc)
    xf = fftfreq(N, 1 / FS_ADC)
    
    # Tomamos apenas a metade positiva do espectro da FFT
    freqs_positivas = xf[:N//2]
    amplitude_fft = (2.0 / N) * np.abs(yf[:N//2])
    # O termo DC (frequência 0) não deve ser multiplicado por 2
    amplitude_fft[0] = amplitude_fft[0] / 2.0 

    # --- Criação das Figuras ---
    plt.figure(figsize=(12, 5))
    
    # Gráfico 1: Domínio do Tempo
    plt.subplot(1, 2, 1)
    plt.plot(tempo * 1000, dados_adc, 'b.-', label='Amostras ADC')
    plt.title(f"Tempo - {titulo_teste}")
    plt.xlabel("Tempo (ms)")
    plt.ylabel("Amplitude (Digital 0-4095)")
    plt.grid(True)
    plt.legend()
    
    # Gráfico 2: Domínio da Frequência (Espectro)
    plt.subplot(1, 2, 2)
    plt.stem(freqs_positivas, amplitude_fft, 'r', markerfmt='ro', basefmt=" ")
    plt.title(f"Espectro (FFT) - {titulo_teste}")
    plt.xlabel("Frequência (Hz)")
    plt.ylabel("Magnitude")
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()


def normalizar_para_dac(sinal_continuo):
    """Normaliza e satura um sinal genérico para a faixa de 12 bits do DAC (0 a 4095)."""
    
    sinal_digital = (sinal_continuo * 0.95 + 1.0) * 2047.5
    # Garante estritamente que nenhum valor saia dos limites do hardware
    sinal_digital = np.clip(sinal_digital, 0, 4095)
    return sinal_digital.astype(np.uint16)


# =========================================================================
# GERADORES DE SINAIS PARA OS TESTES DO ROTEIRO
# =========================================================================

def rodar_teste(ser, opcao):
    t_dac = np.arange(TAM_BUFFER_DAC) / FS_DAC
    
    if opcao == '1':
        titulo = "Caso de Referencia (Senoide de Baixa Frequencia)"
        print(f"\n--- Executando: {titulo} ---")
        freq_fundamental = 50.0  
        sinal = np.sin(2 * np.pi * freq_fundamental * t_dac)
        
    elif opcao == '2':
        titulo = "Variacao de Frequencia (Frequencia Elevada)"
        print(f"\n--- Executando: {titulo} ---")
        freq_fundamental = 3000.0 
        sinal = np.sin(2 * np.pi * freq_fundamental * t_dac)
        
    elif opcao == '3':
        titulo = "Adicao de Harmonicas"
        print(f"\n--- Executando: {titulo} ---")
        freq_fundamental = 50.0  # Hz
        sinal = (0.6 * np.sin(2 * np.pi * freq_fundamental * t_dac) + 
                 0.4 * np.sin(2 * np.pi * (3 * freq_fundamental) * t_dac) + 
                 0.2 * np.sin(2 * np.pi * (5 * freq_fundamental) * t_dac))
        # Reduz a amplitude global para não estourar a normalização após a soma das harmônicas
        sinal = sinal / 1.6
        
    elif opcao == '4':
        titulo = f" Taxa de envio de dados ao DAC {FS_DAC}Hz"
        print(f"\n--- Executando: {titulo} ---")
        freq_fundamental = 50.0  
        sinal = np.sin(2 * np.pi * freq_fundamental * t_dac)
        
    elif opcao == '5':
        titulo = "Variacao da Taxa de Amostragem"
        print(f"\n--- Executando: {titulo} ---")
        freq_aliasing = 950 
        print(f"Injetando {freq_aliasing} Hz. Nyquist teórico é {FS_ADC / 2} Hz.")
        sinal = np.sin(2 * np.pi * freq_aliasing * t_dac)
        titulo += f" Taxa de amostragem {FS_ADC}, Injetado {freq_aliasing}Hz"
        
    else:
        return

    # Processo de envio, captura e plotagem
    sinal_dac = normalizar_para_dac(sinal)
    
    if enviar_vetor_dac(ser, sinal_dac):
        time.sleep(0.5)
        ser.reset_input_buffer()
        print("Coletando dados do ADC...")
        dados_adc = receber_vetor_adc(ser)
        
        if dados_adc is not None:
            plotar_sinal(dados_adc, titulo)


# =========================================================================
# LOOP PRINCIPAL DO MENU
# =========================================================================

def main():
    print("--- Interface Python para o Estudo Dirigido 4 ---")
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=3) as ser:
            print(f"Porta {SERIAL_PORT} aberta com sucesso.")
            time.sleep(1)
            
            while True:
                print("\n" + "="*45)
                print("      MENU DE TESTES      ")
                print("="*45)
                print("1. Caso de Referência")
                print("2. Variação da Frequência ")
                print("3. Adição de Harmônicas ")
                print("4. Variação do Número de Pontos ")
                print("5. Variação da Taxa de Amostragem ")
                print("0. Sair")
                print("="*45)
                
                escolha = input("Selecione o teste que deseja rodar: ")
                
                if escolha == '0':
                    print("Encerrando o script.")
                    break
                elif escolha in ['1', '2', '3', '4', '5']:
                    rodar_teste(ser, escolha)
                else:
                    print("Opção inválida. Escolha um número de 0 a 5.")
                    
    except serial.SerialException as e:
        print(f"\nErro de conexão serial: {e}")
        print("Verifique se o C2000 está conectado e se a porta COM está correta.")

if __name__ == "__main__":
    main()