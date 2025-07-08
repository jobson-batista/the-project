import requests
import time
import logging
import os
from datetime import datetime

# Configuração de logging
logging.basicConfig(filename='arbitrage_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_message_telegram(message):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message}
    )

    print('\nCotação enviada!')

def get_binance_prices():
    """Obtém os preços de ask e bid para USDT/BRL da Binance."""
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/bookTicker?symbol=USDTBRL")
        response.raise_for_status()  # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
        data = response.json()
        ask = float(data['askPrice'])
        bid = float(data['bidPrice'])
        return ask, bid
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados da Binance: {e}")
        return None, None

def get_bybit_prices():
    """Obtém os preços de ask e bid para USDT/BRL da Bybit."""
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=USDTBRL")
        response.raise_for_status()
        data = response.json()
        if data['retCode'] == 0 and data['result']['list']:
            ticker = data['result']['list'][0]
            ask = float(ticker['ask1Price'])
            bid = float(ticker['bid1Price'])
            return ask, bid
        else:
            logging.error(f"Erro ao obter dados da Bybit: {data.get('retMsg', 'Mensagem de erro não disponível')}")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados da Bybit: {e}")
        return None, None

def get_bitrue_prices():
    """Obtém os preços de ask e bid para USDT/BRL da Bitrue."""
    try:
        response = requests.get("https://api.bitrue.com/api/v1/ticker/bookTicker?symbol=USDTBRL")
        response.raise_for_status() 
        data = response.json()
        print(response)
        ask = float(data['askPrice'])
        bid = float(data['bidPrice'])
        return ask, bid
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados da Bitrue: {e}")
        return None, None

def get_novadax_prices():
    """Obtém os preços de ask e bid para USDT/BRL da Novadax."""
    try:
        response = requests.get("https://api.novadax.com/v1/market/tickers")
        response.raise_for_status()
        data = response.json()
        if data['code'] == 'A10000' and data['data']:
            for ticker in data['data']:
                if ticker['symbol'] == 'USDT_BRL':
                    ask = float(ticker['ask'])
                    bid = float(ticker['bid'])
                    return ask, bid
            logging.error("Par USDT_BRL não encontrado na Novadax.")
            return None, None
        else:
            logging.error(f"Erro ao obter dados da Novadax: {data.get('message', 'Mensagem de erro não disponível')}")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados da Novadax: {e}")
        return None, None

def get_foxbit_prices():
    """Obtém os preços de ask e bid para USDT/BRL da Foxbit."""
    try:
        response = requests.get("https://docs-otc.foxbit.com.br/api/v1/markets")
        response.raise_for_status()
        data = response.json()
        
        logging.warning("API da Foxbit não fornece ask/bid diretamente para o par USDT/BRL. Necessita de investigação adicional.")
        return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao obter dados da Foxbit: {e}")
        return None, None

def calculate_spread(prices):
    """Calcula o spread entre a corretora com o maior preço de venda (menor ask) e a corretora com o menor preço de compra (maior bid)."""
    best_ask = {'exchange': None, 'price': float('inf')}
    best_bid = {'exchange': None, 'price': 0.0}

    for exchange, ask, bid in prices:
        if ask is not None and bid is not None:
            if ask < best_ask['price']:
                best_ask['price'] = ask
                best_ask['exchange'] = exchange
            if bid > best_bid['price']:
                best_bid['price'] = bid
                best_bid['exchange'] = exchange

    if best_ask['exchange'] and best_bid['exchange']:
        spread_reais = best_bid['price'] - best_ask['price']
        if best_ask['price'] > 0:
            spread_percentual = (spread_reais / best_ask['price']) * 100
        else:
            spread_percentual = 0.0
        return best_ask, best_bid, spread_reais, spread_percentual
    return None, None, None, None

def simulate_arbitrage(capital, best_ask, best_bid):
    """Simula uma operação de arbitragem com um capital inicial."""
    if best_ask and best_bid and best_ask['price'] > 0:
        usdt_comprado = capital / best_ask['price']
        brl_vendido = usdt_comprado * best_bid['price']
        lucro_bruto_reais = brl_vendido - capital
        lucro_bruto_percentual = (lucro_bruto_reais / capital) * 100
        return usdt_comprado, brl_vendido, lucro_bruto_reais, lucro_bruto_percentual
    return None, None, None, None

def main():
    
    print("Iniciando monitoramento de arbitragem... (Ctrl+C para parar)")

    while True:
        exchange_prices = []

        # Obter preços de cada corretora
        binance_ask, binance_bid = get_binance_prices()
        if binance_ask and binance_bid: exchange_prices.append(('Binance', binance_ask, binance_bid))

        bybit_ask, bybit_bid = get_bybit_prices()
        if bybit_ask and bybit_bid: exchange_prices.append(('Bybit', bybit_ask, bybit_bid))

        # bitrue_ask, bitrue_bid = get_bitrue_prices()
        # if bitrue_ask and bitrue_bid: exchange_prices.append(('Bitrue', bitrue_ask, bitrue_bid))

        novadax_ask, novadax_bid = get_novadax_prices()
        if novadax_ask and novadax_bid: exchange_prices.append(('Novadax', novadax_ask, novadax_bid))

        foxbit_ask, foxbit_bid = get_foxbit_prices()
        if foxbit_ask and foxbit_bid: exchange_prices.append(('Foxbit', foxbit_ask, foxbit_bid))

        if len(exchange_prices) < 2: # Precisa de pelo menos duas corretoras para calcular spread
            print("\nNão há dados suficientes de corretoras para calcular o spread. Tentando novamente em 15 segundos...")
            time.sleep(15)
            continue

        # Calcular spread
        best_ask, best_bid, spread_reais, spread_percentual = calculate_spread(exchange_prices)

        os.system("clear")

        if spread_reais is not None:
            print(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            print("Cotações:")
            for exchange, ask, bid in exchange_prices:
                print(f"  {exchange}: \tAsk = R${ask:.4f},\tBid = R${bid:.4f}")

            print(f"\nMelhor Compra (menor Ask): {best_ask['exchange']} a R${best_ask['price']:.4f}")
            print(f"Melhor Venda (maior Bid): {best_bid['exchange']} a R${best_bid['price']:.4f}")
            print(f"\nSpread em R$: {spread_reais:.4f}")
            print(f"Spread Percentual: {spread_percentual:.4f}%")

            # Simulação de arbitragem
            capital_inicial = 100
            usdt_comprado, brl_vendido, lucro_bruto_reais, lucro_bruto_percentual = simulate_arbitrage(capital_inicial, best_ask, best_bid)

            if lucro_bruto_reais is not None:
                print(f"\nSimulação de Arbitragem com R${capital_inicial:.2f}:")
                print(f"\tCompraria {usdt_comprado:.4f} USDT na {best_ask['exchange']} por R${best_ask['price']:.4f}")
                print(f"\tVenderia {usdt_comprado:.4f} USDT na {best_bid['exchange']} por R${best_bid['price']:.4f} (total R${brl_vendido:.2f})")
                print(f"\tLucro Bruto Estimado: R${lucro_bruto_reais:.4f} ({lucro_bruto_percentual:.4f}%)")

                # Registrar no log se o spread for maior que 0.5%
                if spread_percentual > 0.5:
                    log_message = f"Oportunidade de Arbitragem: Spread {spread_percentual:.4f}% (R${spread_reais:.4f}) - Comprar na {best_ask['exchange']} ({best_ask['price']:.4f}) e Vender na {best_bid['exchange']} ({best_bid['price']:.4f}). Lucro Bruto Estimado: R$ {lucro_bruto_reais:.4f}"
                    logging.info(log_message)
                    print(f"\nOPORTUNIDADE REGISTRADA NO LOG: {log_message}")
                    #log_message = f"Oportunidade de Arbitragem: \n\nSpread {spread_percentual:.4f}% (R${spread_reais:.4f}) - Comprar na {best_ask['exchange']} ({best_ask['price']:.4f}) e Vender na {best_bid['exchange']} ({best_bid['price']:.4f}). \nLucro Bruto Estimado: R$ {lucro_bruto_reais:.4f}"
                    log_message = f"🚨 Não Entre em Pânico - Possível Oportunidade"
                    log_message += f"\n\nSimulação de Arbitragem com R${capital_inicial:.2f}:"
                    log_message += f"\n\nComprar na {best_ask['exchange']} por R${best_ask['price']:.4f}"
                    log_message += f"\n\nVender na {best_bid['exchange']} por R${best_bid['price']:.4f} \n\nResultado R$ {brl_vendido:.2f}"
                    log_message += f"\n\nLucro Bruto Estimado: R${lucro_bruto_reais:.4f} ({lucro_bruto_percentual:.4f}%)"
                    send_message_telegram(log_message)
        else:
            print("\nNão foi possível calcular o spread. Verifique os dados das corretoras.")

        time.sleep(5)

if __name__ == "__main__":
    main()