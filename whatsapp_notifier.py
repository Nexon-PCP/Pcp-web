"""
WhatsApp Notifier - Envia notificações via WhatsApp Web
Versão Melhorada com Tratamento de Erros
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import os


class WhatsAppNotifier:
    """Classe para enviar notificações via WhatsApp Web"""
    
    def __init__(self, chromedriver_path, group_name):
        """
        Inicializa o notificador
        
        Args:
            chromedriver_path: Caminho para o chromedriver.exe
            group_name: Nome do grupo do WhatsApp
        """
        self.chromedriver_path = chromedriver_path
        self.group_name = group_name
        self.driver = None
        self.is_connected = False
        self.profile_path = os.path.expanduser("~/.wpp_profile")
    
    def connect(self):
        """Conecta ao WhatsApp Web com configurações otimizadas"""
        try:
            print("\n🔄 Conectando ao WhatsApp Web...")
            print(f"   ChromeDriver: {self.chromedriver_path}")
            print(f"   Grupo: {self.group_name}")
            
            chrome_options = Options()
            
            # Adicionar perfil do usuário para manter login
            if not os.path.exists(self.profile_path):
                os.makedirs(self.profile_path)
            chrome_options.add_argument(f"user-data-dir={self.profile_path}")
            
            # Configurações otimizadas
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2
            })
            
            print("   Iniciando Chrome...")
            self.driver = webdriver.Chrome(
                self.chromedriver_path,
                options=chrome_options
            )
            
            print("   Acessando WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            
            print("\n📱 ESCANEIE O QR CODE COM SEU CELULAR!")
            print("⏳ Aguardando conexão (máximo 60 segundos)...\n")
            
            # Aguardar até que o chat seja carregado (com timeout maior)
            try:
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "_8nE46"))
                )
            except:
                # Se não encontrar a classe, tenta outra abordagem
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@role='listitem']"))
                )
            
            self.is_connected = True
            print("✅ Conectado ao WhatsApp Web com sucesso!\n")
            return True
            
        except Exception as e:
            print(f"\n❌ Erro ao conectar: {str(e)}\n")
            self.is_connected = False
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            return False
    
    def find_group(self):
        """Encontra o grupo pelo nome com múltiplas tentativas"""
        try:
            print(f"🔍 Procurando grupo '{self.group_name}'...")
            
            # Tentar encontrar a caixa de pesquisa
            search_xpaths = [
                "//input[@title='Pesquisar ou começar uma conversa']",
                "//input[@placeholder='Pesquisar ou começar uma conversa']",
                "//input[@type='text']",
            ]
            
            search_box = None
            for xpath in search_xpaths:
                try:
                    search_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                print("❌ Não foi possível encontrar a caixa de pesquisa")
                return False
            
            search_box.click()
            time.sleep(1)
            search_box.clear()
            search_box.send_keys(self.group_name)
            
            print(f"   Digitado: {self.group_name}")
            time.sleep(2)
            
            # Tentar clicar no grupo
            group_xpaths = [
                f"//span[@title='{self.group_name}']",
                f"//div[@title='{self.group_name}']",
                f"//span[contains(text(), '{self.group_name}')]",
            ]
            
            group = None
            for xpath in group_xpaths:
                try:
                    group = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    if group:
                        break
                except:
                    continue
            
            if not group:
                print(f"❌ Grupo '{self.group_name}' não encontrado")
                print("   Verifique se o nome está exato")
                return False
            
            group.click()
            time.sleep(2)
            
            print(f"✅ Grupo '{self.group_name}' encontrado!\n")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao encontrar grupo: {str(e)}\n")
            return False
    
    def send_message(self, message):
        """Envia uma mensagem para o grupo com tratamento robusto"""
        try:
            if not self.is_connected:
                print("❌ Não conectado ao WhatsApp Web!")
                return False
            
            # Múltiplas tentativas para encontrar o campo de mensagem
            message_xpaths = [
                "//div[@contenteditable='true'][@data-tab='10']",
                "//div[@contenteditable='true'][@role='textbox']",
                "//div[@contenteditable='true']",
            ]
            
            message_box = None
            for xpath in message_xpaths:
                try:
                    message_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    if message_box:
                        break
                except:
                    continue
            
            if not message_box:
                print("❌ Não foi possível encontrar o campo de mensagem")
                return False
            
            message_box.click()
            time.sleep(0.5)
            message_box.clear()
            
            # Enviar mensagem
            message_box.send_keys(message)
            time.sleep(0.5)
            
            # Enviar (pressionar Enter ou clicar no botão)
            try:
                message_box.send_keys(Keys.ENTER)
            except:
                send_button = self.driver.find_element(
                    By.XPATH,
                    "//button[@aria-label='Enviar']"
                )
                send_button.click()
            
            print(f"✅ Mensagem enviada com sucesso!\n")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {str(e)}\n")
            return False
    
    def disconnect(self):
        """Desconecta do WhatsApp Web"""
        try:
            if self.driver:
                self.driver.quit()
                self.is_connected = False
                print("✅ Desconectado do WhatsApp Web\n")
        except Exception as e:
            print(f"❌ Erro ao desconectar: {str(e)}\n")
    
    def reconnect(self):
        """Reconecta ao WhatsApp Web"""
        try:
            print("\n🔄 Reconectando ao WhatsApp Web...")
            self.disconnect()
            time.sleep(3)
            if self.connect():
                time.sleep(2)
                if self.find_group():
                    return True
            return False
        except Exception as e:
            print(f"❌ Erro ao reconectar: {str(e)}\n")
            return False
