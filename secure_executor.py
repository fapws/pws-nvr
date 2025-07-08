#!/usr/bin/env python3
"""
Secure Command Executor per operazioni privilegiate
Sostituisce i comandi sudo non sicuri con implementazioni validate
"""

import subprocess
import logging
import os
import shlex
from pathlib import Path

class SecureCommandExecutor:
    """Esecuzione sicura di comandi di sistema"""
    
    # Comandi consentiti con i loro argomenti validi
    ALLOWED_COMMANDS = {
        'mount': {
            'binary': '/bin/mount',
            'allowed_args': ['-t', '-o', 'defaults', 'noatime', 'nodiratime', 'ext4'],
            'max_args': 6
        },
        'umount': {
            'binary': '/bin/umount',
            'allowed_args': [],
            'max_args': 2
        },
        'chown': {
            'binary': '/bin/chown',
            'allowed_args': ['-R'],
            'max_args': 4
        },
        'chmod': {
            'binary': '/bin/chmod',
            'allowed_args': ['-R'],
            'max_args': 4
        },
        'systemctl': {
            'binary': '/bin/systemctl',
            'allowed_args': ['start', 'stop', 'restart', 'is-active', 'status'],
            'max_args': 3
        },
        'reboot': {
            'binary': '/sbin/reboot',
            'allowed_args': [],
            'max_args': 1
        },
        'shutdown': {
            'binary': '/sbin/shutdown',
            'allowed_args': ['-h', 'now'],
            'max_args': 3
        },
        'tailscale': {
            'binary': '/usr/bin/tailscale',
            'allowed_args': ['up', 'down', 'status', '--advertise-exit-node'],
            'max_args': 3
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _validate_command(self, command, args):
        """Valida un comando e i suoi argomenti"""
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(f"Comando non consentito: {command}")
        
        cmd_config = self.ALLOWED_COMMANDS[command]
        
        # Verifica il numero di argomenti
        if len(args) > cmd_config['max_args']:
            raise ValueError(f"Troppi argomenti per {command}: {len(args)}")
        
        # Verifica che gli argomenti siano consentiti
        for arg in args:
            if arg.startswith('-') and arg not in cmd_config['allowed_args']:
                raise ValueError(f"Argomento non consentito per {command}: {arg}")
            
            # Prevenzione path traversal
            if '../' in arg or '..' in arg:
                raise ValueError(f"Path traversal rilevato in: {arg}")
        
        return True
    
    def _sanitize_path(self, path):
        """Sanitizza un percorso di filesystem"""
        try:
            # Risolve il percorso assoluto
            resolved_path = Path(path).resolve()
            
            # Verifica che il percorso sia in directory consentite
            allowed_paths = [
                '/media',
                '/mnt',
                '/home',
                '/tmp',
                '/var'
            ]
            
            path_str = str(resolved_path)
            if not any(path_str.startswith(allowed) for allowed in allowed_paths):
                raise ValueError(f"Percorso non consentito: {path_str}")
            
            return path_str
        except Exception as e:
            raise ValueError(f"Percorso non valido: {path}")
    
    def execute_command(self, command, args, timeout=30):
        """Esegue un comando in modo sicuro"""
        try:
            # Validazione
            self._validate_command(command, args)
            
            # Costruzione comando
            cmd_config = self.ALLOWED_COMMANDS[command]
            cmd_list = [cmd_config['binary']] + args
            
            # Sanitizzazione percorsi se necessario
            if command in ['mount', 'umount', 'chown', 'chmod']:
                sanitized_args = []
                for arg in args:
                    if arg.startswith('/') or arg.startswith('.'):
                        sanitized_args.append(self._sanitize_path(arg))
                    else:
                        sanitized_args.append(arg)
                cmd_list = [cmd_config['binary']] + sanitized_args
            
            # Log del comando (senza credenziali)
            self.logger.info(f"Eseguendo comando sicuro: {' '.join(cmd_list)}")
            
            # Esecuzione
            result = subprocess.run(
                ['sudo'] + cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                self.logger.error(f"Comando fallito: {result.stderr}")
                return False, result.stderr
            
            return True, result.stdout
            
        except Exception as e:
            self.logger.error(f"Errore nell'esecuzione del comando: {e}")
            return False, str(e)
    
    def mount_disk(self, device, mount_point, fs_type='ext4'):
        """Monta un disco in modo sicuro"""
        args = ['-t', fs_type, '-o', 'defaults,noatime,nodiratime', device, mount_point]
        return self.execute_command('mount', args)
    
    def umount_disk(self, mount_point):
        """Smonta un disco in modo sicuro"""
        args = [mount_point]
        return self.execute_command('umount', args)
    
    def set_ownership(self, path, owner, recursive=False):
        """Imposta proprietario di file/directory"""
        args = ['-R', f'{owner}:{owner}', path] if recursive else [f'{owner}:{owner}', path]
        return self.execute_command('chown', args)
    
    def set_permissions(self, path, permissions, recursive=False):
        """Imposta permessi di file/directory"""
        args = ['-R', permissions, path] if recursive else [permissions, path]
        return self.execute_command('chmod', args)
    
    def systemctl_service(self, action, service):
        """Controlla servizi systemd"""
        args = [action, service]
        
        # Comandi di lettura stato non richiedono sudo
        if action in ['is-active', 'is-enabled', 'status']:
            try:
                cmd_config = self.ALLOWED_COMMANDS['systemctl']
                cmd_list = [cmd_config['binary']] + args
                
                self.logger.info(f"Eseguendo comando systemctl senza sudo: {' '.join(cmd_list)}")
                
                result = subprocess.run(
                    cmd_list,  # Senza sudo per comandi di lettura
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False
                )
                
                return result.returncode == 0, result.stdout.strip()
                
            except Exception as e:
                self.logger.error(f"Errore controllo servizio {service}: {e}")
                return False, str(e)
        else:
            # Comandi di controllo (start, stop, restart) richiedono sudo
            return self.execute_command('systemctl', args)
    
    def system_reboot(self):
        """Riavvia il sistema"""
        return self.execute_command('reboot', [])
    
    def system_shutdown(self):
        """Spegne il sistema"""
        return self.execute_command('shutdown', ['-h', 'now'])
    
    def tailscale_action(self, action, extra_args=None):
        """Gestisce Tailscale"""
        args = [action]
        if extra_args:
            args.extend(extra_args)
        return self.execute_command('tailscale', args)
