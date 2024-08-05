# Stage 1: Base stage
FROM python:3.12-slim AS base

ARG USERNAME=appuser
ARG USER_UID=1001
ARG USER_GID=$USER_UID
ARG ENVIRONMENT=production

# Install necessary packages
RUN set -ex \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        wget \
        gnupg \
        libgtk-3-0 \
        libdbus-glib-1-2 \
        libgconf-2-4 \
        libasound2 \
        libpulse0 \
        libxtst6 \
        libxss1 \
        libnss3 \
        libappindicator3-1 \
        xauth \
        xvfb \
        unzip \
        bzip2 \
        git \
        curl \
        procps \
        openssh-client \
        tzdata \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    # Set timezone to PDT
    && ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    # Remove imagemagick due to https://security-tracker.debian.org/tracker/CVE-2019-10131
    && apt-get purge -y imagemagick imagemagick-6-common \
    && apt-get upgrade -y \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install Firefox
RUN wget -q "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" -O /firefox.tar.bz2 && \
    tar xjf /firefox.tar.bz2 -C /opt/ && \
    rm /firefox.tar.bz2 && \
    ln -s /opt/firefox/firefox /usr/bin/firefox

# Install Geckodriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz" -O /geckodriver.tar.gz && \
    tar -xzf /geckodriver.tar.gz -C /usr/local/bin && \
    rm /geckodriver.tar.gz

ENV WORKDIR_PATH=/code
WORKDIR $WORKDIR_PATH

COPY --chown=$USERNAME:$USER_GID ./src ./src
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir --upgrade --disable-pip-version-check -r src/requirements.txt 

# Stage 2: Development stage
FROM base AS development

# Conditionally install and configure Oh My Zsh for development environment
ARG USERNAME
ARG USER_UID
ARG USER_GID

# Conditionally install and configure Oh My Zsh for development environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    zsh \
    fonts-powerline \
    gcc \
    python3-dev \
    && apt-get upgrade -y \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* && \
    # Set Zsh as the default shell for the user by modifying /etc/passwd
    sed -i "s|/home/${USERNAME}:/bin/sh|/home/${USERNAME}:/usr/bin/zsh|" /etc/passwd

# Switch to non-root user
USER $USERNAME

RUN \
    # Install Oh My Zsh
    sh -c "$(wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O -)" --unattended && \
    # Install Zsh plugins and theme
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-completions && \
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/themes/powerlevel10k && \
    # Customize Zsh prompt
    echo 'if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then' >> /home/${USERNAME}/.zshrc \
    && echo '  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"' >> /home/${USERNAME}/.zshrc \
    && echo 'fi' >> /home/${USERNAME}/.zshrc \
    && sed -i 's/ZSH_THEME="robbyrussell"/ZSH_THEME="powerlevel10k\/powerlevel10k"/' /home/${USERNAME}/.zshrc \
    && sed -i 's/plugins=(git)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting zsh-completions)/' /home/${USERNAME}/.zshrc \
    && echo "source \${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" >> /home/${USERNAME}/.zshrc \
    && echo "source $HOME/.p10k.zsh" >> /home/${USERNAME}/.zshrc 

# Conditionally copy Powerlevel10k configuration file for development environment
COPY --chown=$USERNAME:$USER_GID .dot_files/.p10k.zsh /home/${USERNAME}/.p10k.zsh

# Copy the SSH keys (Ensure .ssh directory exists in the build context)
COPY --chown=$USERNAME:$USER_GID .dot_files/ssh_key* /home/${USERNAME}/.ssh/
RUN chmod 700 /home/${USERNAME}/.ssh && chmod 600 /home/${USERNAME}/.ssh/* && chmod 644 /home/${USERNAME}/.ssh/*.pub

# Add SSH key to the SSH agent
RUN echo "eval \$(ssh-agent -s) && ssh-add /home/${USERNAME}/.ssh/ssh_key" >> /home/${USERNAME}/.zshrc

# Install Jupyter for development environment
RUN pip install jupyter 

# Start the main application and keep the container running
CMD ["sh", "-c", "python src/main.py & tail -f /dev/null"]

# Stage 3: Production stage
FROM base AS production
ARG ENVIRONMENT
ARG USERNAME

# Ensure bash is the default shell
RUN chsh -s /bin/bash $USERNAME

# Switch to non-root user
USER $USERNAME

# Start the main application and keep the container running
CMD ["sh", "-c", "python src/main.py & tail -f /dev/null"]
