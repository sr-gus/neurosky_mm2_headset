from db_manager import MongoDBManager
from session_manager import SessionManager
import signal
import sys

HEADSET_PORT = 'COM10'

def main():
    db_manager = MongoDBManager()
    session_manager = SessionManager(db_manager, HEADSET_PORT)

    def end_session(signal_received=None, frame=None):
        if session_manager.is_collecting:
            session_manager.end_session()
            print('\nSesión terminada.')
        sys.exit(0)

    signal.signal(signal.SIGINT, end_session)

    while True:
        print('1. Iniciar nueva sesión')
        print('2. Ver datos de sesiones anteriores')
        print('3. Salir')
        choice = input('Selecciona una opción: ')

        if choice == '1':
            user_id = input('Ingresa el nombre del usuario: ')
            session_manager.start_new_session(user_id)
            print('Sesión iniciada. Presiona Ctrl+C para detener.')

            if session_manager.is_collecting:
                try:
                    session_manager.initialize_plot()  
                    session_manager.end_session()
                except KeyboardInterrupt:
                    end_session()

        elif choice == '2':
            user_id = input('Ingresa el nombre del usuario: ')
            sessions = db_manager.get_user_sessions(user_id)
            sessions = list(sessions)
            if not sessions:
                print('No hay sesiones registradas para este usuario.')
                continue

            for idx, session in enumerate(sessions):
                print(f'{idx + 1}. Iniciada el {session["start_time"]} - Finalizada el {session["end_time"]}')

            user_input = input('Selecciona una sesión para ver los datos: ')
            while not user_input.isdigit():
                print('Entrada inválida')
                user_input = input('Selecciona una sesión para ver los datos: ')

            session_choice = int(user_input) - 1
            session_data = db_manager.get_session_data(sessions[session_choice]['_id'])
            if session_data:
                print('1. Exportar a CSV')
                print('2. Ver gráfica')
                print('3. Ver espectro de frecuencia')
                print('4. Ver espectrograma')

                user_input = input('Selecciona una opción: ')
                while not user_input.isdigit():
                    print('Entrada inválida')
                    user_input = input('Selecciona una opción: ')

                export_choice = int(user_input)

                if export_choice == 1:
                    filename = input('Ingresa el nombre del archivo CSV: ')
                    session_manager.export_session_to_csv(session_data, filename)
                    print(f'Datos exportados a {filename}')

                elif export_choice == 2:
                    session_manager.plot_session_data(session_data)

                elif export_choice == 3:
                    session_manager.plot_frequency_spectrum(session_data)

                elif export_choice == 4:
                    session_manager.plot_spectrogram(session_data)

            else: 
                print('Error al procesar la sesión')

        elif choice == '3':
            print('Saliendo...')
            end_session()

        else:
            print('Opción no válida. Intenta de nuevo.')

if __name__ == '__main__':
    main()
