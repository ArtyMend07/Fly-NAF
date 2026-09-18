import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import mss
import numpy as np
import cv2
import config

def main():
    cx = config.CAMERA_DETECTION.patch_x
    cy = config.CAMERA_DETECTION.patch_y
    csize = config.CAMERA_DETECTION.patch_size
    offset = csize // 2
    bbox = {'top': cy - offset, 'left': cx - offset, 'width': csize, 'height': csize}
    
    print('Aguardando 3s para capturar ref-fechada. Volte para o jogo e fique na sala!')
    time.sleep(3)
    with mss.MSS() as sct:
        ref_img = np.array(sct.grab(bbox))
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGRA2GRAY).astype(np.float32)
    
    print('Referencia capturada! Gravando log em logs/mse_camera.txt...')
    print('Abra a camera, espere 2 segundos, feche e depois de ALT+TAB para fechar o script.')
    
    os.makedirs('logs', exist_ok=True)
    with open('logs/mse_camera.txt', 'w') as f:
        f.write('--- LOG DE MSE DA CAMERA ---\n')
        
    with mss.MSS() as sct:
        try:
            while True:
                cur_img = np.array(sct.grab(bbox))
                cur_gray = cv2.cvtColor(cur_img, cv2.COLOR_BGRA2GRAY).astype(np.float32)
                mse = float(np.mean((cur_gray - ref_gray) ** 2))
                
                with open('logs/mse_camera.txt', 'a') as f:
                    f.write(f'MSE: {mse:.1f}\n')
                    
                print(f'\rGravando... (MSE Atual: {mse:.1f})', end='')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print('\nFinalizado pelo usuario.')

if __name__ == '__main__':
    main()
